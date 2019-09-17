from sklearn.utils.metaestimators import _BaseComposition
import numpy as np
import datetime
import os

from photonai.base.cache_manager import CacheManager
from photonai.helper.helper import PhotonDataHelper


class PhotonPipeline(_BaseComposition):

    def __init__(self, elements):
        self.elements = elements

        self.current_config = None
        # caching stuff
        self.caching = False
        self._fold_id = None
        self._cache_folder = None
        self.time_monitor = {'fit': [], 'transform_computed': [], 'transform_cached': [], 'predict': []}
        self.cache_man = None

        # helper for single subject caching
        self._single_subject_caching = False
        self._fix_fold_id = False
        self._do_not_delete_cache_folder = False
        self._parallel_use = False

        # used in parallelization
        self.skip_loading = False

    def set_lock(self, lock):
        self.cache_man.lock = lock

    @property
    def single_subject_caching(self):
        return self._single_subject_caching

    @single_subject_caching.setter
    def single_subject_caching(self, value: bool):
        if value:
            self._fix_fold_id = True
            self._do_not_delete_cache_folder = True
        else:
            self._fix_fold_id = False
            self._do_not_delete_cache_folder = False
        self._single_subject_caching = value

    @property
    def fold_id(self):
        return self._fold_id

    @fold_id.setter
    def fold_id(self, value):
        if value is None:
            self._fold_id = ''
            # we dont need group-wise caching if we have no inner fold id
            self.caching = False
            self.cache_man = None
        else:
            if self._fix_fold_id:
                self._fold_id = "fixed_fold_id"
            else:
                self._fold_id = str(value)
            self.caching = True
            self.cache_man = CacheManager(self._fold_id, self.cache_folder, self._parallel_use)

    @property
    def cache_folder(self):
        return self._cache_folder

    @cache_folder.setter
    def cache_folder(self, value):

        if not self._do_not_delete_cache_folder:
            self._cache_folder = value
        else:
            if isinstance(value, str) and not value.endswith("DND"):
                self._cache_folder = value + "DND"
            else:
                self._cache_folder = value

        if isinstance(self._cache_folder, str):
            self.caching = True
            if not os.path.isdir(self._cache_folder):
                os.makedirs(self._cache_folder)
            self.cache_man = CacheManager(self._fold_id, self.cache_folder, self._parallel_use)
        else:
            self.caching = False

    def get_params(self, deep=True):
        """Get parameters for this estimator.
        Parameters
        ----------
        deep : boolean, optional
            If True, will return the parameters for this estimator and
            contained subobjects that are estimators.
        Returns
        -------
        params : mapping of string to any
            Parameter names mapped to their values.
        """
        return self._get_params('elements', deep=deep)

    def set_params(self, **kwargs):
        """Set the parameters of this estimator.
        Valid parameter keys can be listed with ``get_params()``.
        Returns
        -------
        self
        """
        if self.current_config is not None and len(self.current_config) > 0:
            if kwargs is not None and len(kwargs) == 0:
                raise ValueError("Pipeline cannot set parameters to elements with an emtpy dictionary. Old values persist")
        self.current_config = kwargs
        self._set_params('elements', **kwargs)

        return self

    def _validate_elements(self):
        names, estimators = zip(*self.elements)

        # validate names
        self._validate_names(names)

        # validate estimators
        transformers = estimators[:-1]
        estimator = estimators[-1]

        for t in transformers:
            if t is None:
                continue
            if not (hasattr(t, "fit") or not hasattr(t, "transform")):
                raise TypeError("All intermediate elements should be "
                                "transformers and implement fit and transform."
                                " '%s' (type %s) doesn't" % (t, type(t)))

        # We allow last estimator to be None as an identity transformation
        if estimator is not None and not hasattr(estimator, "fit"):
            raise TypeError("Last step of Pipeline should implement fit. "
                            "'%s' (type %s) doesn't"
                            % (estimator, type(estimator)))

    def fit(self, X, y=None, **kwargs):

        self._validate_elements()
        X, y, kwargs = self._caching_fit_transform(X, y, kwargs, fit=True)

        if self._final_estimator is not None:
            fit_start_time = datetime.datetime.now()
            self._final_estimator.fit(X, y, **kwargs)
            n = PhotonDataHelper.find_n(X)
            fit_duration = (datetime.datetime.now() - fit_start_time).total_seconds()
            self.time_monitor['fit'].append((self.elements[-1][0], fit_duration, n))
        return self

    def check_for_numpy_array(self, list_object):
        # be compatible to list of (image-) files
        if isinstance(list_object, list):
            return np.asarray(list_object)
        else:
            return list_object

    def transform(self, X, y=None, **kwargs):
        """
        Calls transform on every step that offers a transform function
        including the last step if it has the transformer flag,
        and excluding the last step if it has the estimator flag but no transformer flag.

        Returns transformed X, y and kwargs
        """
        if self.single_subject_caching:
            initial_X = np.array(X)
        else:
            initial_X = None

        X, y, kwargs = self._caching_fit_transform(X, y, kwargs)

        if self._final_estimator is not None:
            if self._estimator_type is None:
                if self.caching and self.current_config is not None:
                    X, y, kwargs = self.load_or_save_cached_data(self._final_estimator.name, X, y, kwargs,
                                                                 self._final_estimator,
                                                                 initial_X=initial_X)
                else:
                    X, y, kwargs = self._final_estimator.transform(X, y, **kwargs)

        return X, y, kwargs

    def load_or_save_cached_data(self, name, X, y, kwargs, transformer, fit=False,
                                 needed_for_further_computation=False, initial_X=None):
        if not self.single_subject_caching:
            # if we do it group-wise then its easy
            if self.skip_loading and not needed_for_further_computation:
                # check if data is already calculated
                if self.cache_man.check_cache(name):
                    # if so, do nothing
                    return X, y, kwargs
                else:
                    # otherwise, do the calculation and save it
                    cached_result = None
            else:
                start_time_for_loading = datetime.datetime.now()
                cached_result = self.cache_man.load_cached_data(name)

            if cached_result is None:
                X, y, kwargs = self._do_timed_fit_transform(name, transformer, fit, X, y, **kwargs)

                start_time_saving = datetime.datetime.now()
                self.cache_man.save_data_to_cache(name, (X, y, kwargs))
                saving_duration = (datetime.datetime.now() - start_time_saving).total_seconds()
                self.time_monitor['transform_cached'].append((name, saving_duration, 1))
            else:
                X, y, kwargs = cached_result[0], cached_result[1], cached_result[2]
                loading_duration = (datetime.datetime.now() - start_time_for_loading).total_seconds()
                n = PhotonDataHelper.find_n(X)
                self.time_monitor['transform_cached'].append((name, loading_duration, n))
            return X, y, kwargs
        else:
            # if we do it subject-wise we need to iterate and collect the results
            processed_X, processed_y, processed_kwargs = list(), list(), dict()
            X_uncached, y_uncached, kwargs_uncached, initial_X_uncached = list(), list(), dict(), list()
            list_of_idx_cached, list_of_idx_non_cached = list(), list()

            nr = PhotonDataHelper.find_n(X)
            for start, stop in PhotonDataHelper.chunker(nr, 1):
                # split data in single entities, find key from first element = PATH to file
                X_key, _, _ = PhotonDataHelper.split_data(initial_X, None, {}, start, stop)
                X_batched, y_batched, kwargs_dict_batched = PhotonDataHelper.split_data(X, y, kwargs, start, stop)
                self.cache_man.update_single_subject_state_info(X_key)

                # check if item has been processed
                if self.cache_man.check_cache(name):
                    list_of_idx_cached.append(start)
                else:
                    list_of_idx_non_cached.append(start)
                    X_uncached = PhotonDataHelper.stack_results(X_batched, X_uncached)
                    y_uncached = PhotonDataHelper.stack_results(y_batched, y_uncached)
                    initial_X_uncached = PhotonDataHelper.stack_results(X_key, initial_X_uncached)
                    kwargs_uncached = PhotonDataHelper.join_dictionaries(kwargs_uncached, kwargs_dict_batched)

            # now we know which part can be loaded and which part should be transformed
            # first apply the transformation to the group, then save it single-subject-wise
            if len(list_of_idx_non_cached) > 0:

                # apply transformation groupwise
                new_group_X, new_group_y, new_group_kwargs = self._do_timed_fit_transform(name, transformer, fit,
                                                                                          X_uncached,
                                                                                          y_uncached,
                                                                                          **kwargs_uncached)

                # then save it single
                nr = PhotonDataHelper.find_n(new_group_X)
                for start in range(nr):
                    # split data in single entities
                    X_batched, y_batched, kwargs_dict_batched = PhotonDataHelper.split_data(new_group_X,
                                                                                            new_group_y,
                                                                                            new_group_kwargs,
                                                                                            start, start)
                    X_key, _, _ = PhotonDataHelper.split_data(initial_X_uncached, None, {}, start, start)
                    # we save the data in relation to the input path (X_key = hash(input X))
                    self.cache_man.update_single_subject_state_info(X_key)

                    start_time_saving = datetime.datetime.now()
                    self.cache_man.save_data_to_cache(name, (X_batched, y_batched, kwargs_dict_batched))
                    saving_duration = (datetime.datetime.now() - start_time_saving).total_seconds()
                    self.time_monitor['transform_cached'].append((name, saving_duration, 1))

                # we need to collect the data only when we want to load them
                # we can skip that process if we only want them to get into the cache (case: parallelisation)
                if not self.skip_loading or needed_for_further_computation:
                    # stack results
                    processed_X, processed_y, processed_kwargs = new_group_X, new_group_y, new_group_kwargs

            # afterwards load everything that has been cached
            if len(list_of_idx_cached) > 0:
                if not self.skip_loading or needed_for_further_computation:
                    for cache_idx in list_of_idx_cached:
                        # we identify the data according to the input path (X before any transformation)
                        self.cache_man.update_single_subject_state_info([initial_X[cache_idx]])

                        # time the loading of the cached item
                        start_time_for_loading = datetime.datetime.now()
                        transformed_X, transformed_y, transformed_kwargs = self.cache_man.load_cached_data(name)
                        loading_duration = (datetime.datetime.now() - start_time_for_loading).total_seconds()
                        self.time_monitor['transform_cached'].append((name, loading_duration, PhotonDataHelper.find_n(X)))

                        processed_X, processed_y, processed_kwargs = PhotonDataHelper.join_data(processed_X, transformed_X,
                                                                                                processed_y, transformed_y,
                                                                                                processed_kwargs, transformed_kwargs)
            if not self.skip_loading or needed_for_further_computation:
                # now sort the data in the correct order again
                processed_X, processed_y, processed_kwargs = PhotonDataHelper.resort_splitted_data(processed_X,
                                                                                                   processed_y,
                                                                                                   processed_kwargs,
                                                                                                   PhotonDataHelper.stack_results(list_of_idx_non_cached,
                                                                                                                                  list_of_idx_cached))

            return processed_X, processed_y, processed_kwargs

    def _do_timed_fit_transform(self, name, transformer, fit, X, y, **kwargs):

        n = PhotonDataHelper.find_n(X)

        if fit:
            fit_start_time = datetime.datetime.now()
            transformer.fit(X, y, **kwargs)
            fit_duration = (datetime.datetime.now() - fit_start_time).total_seconds()
            self.time_monitor['fit'].append((name, fit_duration, n))

        transform_start_time = datetime.datetime.now()
        X, y, kwargs = transformer.transform(X, y, **kwargs)
        transform_duration = (datetime.datetime.now() - transform_start_time).total_seconds()
        self.time_monitor['transform_computed'].append((name, transform_duration, n))
        return X, y, kwargs

    def _caching_fit_transform(self, X, y, kwargs, fit=False):

        if self.single_subject_caching:
            initial_X = np.array(X)
        else:
            initial_X = None

        if self.caching:
            # update infos, just in case
            self.cache_man.hash = self._fold_id
            self.cache_man.cache_folder = self.cache_folder
            if not self.single_subject_caching:
                self.cache_man.prepare([name for name, e in self.elements], self.current_config, X)
            else:
                self.cache_man.prepare([name for name, e in self.elements], self.current_config, single_subject_caching=True)
            last_cached_item = None

        # all elements except the last one
        num_steps = len(self.elements) - 1

        for num, (name, transformer) in enumerate(self.elements[:-1]):
            if not self.caching or self.current_config is None or \
                    (hasattr(transformer, 'skip_caching') and transformer.skip_caching):
                X, y, kwargs = self._do_timed_fit_transform(name, transformer, fit, X, y, **kwargs)
            else:
                # load data when the first item occurs that needs new calculation
                if self.cache_man.check_cache(name):
                    # as long as we find something cached, we remember what it was
                    last_cached_item = name
                    # if it is the last step, we need to load the data now
                    if num + 1 == num_steps and not self.skip_loading:
                        X, y, kwargs = self.load_or_save_cached_data(last_cached_item, X, y, kwargs, transformer, fit,
                                                                     initial_X=initial_X)
                else:
                    if last_cached_item is not None:
                        # we load the cached data when the first transformation on this data is upcoming
                        X, y, kwargs = self.load_or_save_cached_data(last_cached_item, X, y, kwargs, transformer, fit,
                                                                     needed_for_further_computation=True,
                                                                     initial_X=initial_X)
                    X, y, kwargs = self.load_or_save_cached_data(name, X, y, kwargs, transformer, fit,
                                                                 initial_X=initial_X)

            # always work with numpy arrays to avoid checking for shape attribute
            X = self.check_for_numpy_array(X)
            y = self.check_for_numpy_array(y)

        return X, y, kwargs

    def predict(self, X, training=False, **kwargs):
        """
        Transforms the data for every step that offers a transform function
        and then calls the estimator with predict on transformed data.
        It returns the predictions made.

        In case the last step is no estimator, it returns the transformed data.
        """

        # first transform
        if not training:
            X, _, kwargs = self.transform(X, y=None, **kwargs)

        # then call predict on final estimator
        if self._final_estimator is not None:
            if self._final_estimator.is_estimator:
                predict_start_time = datetime.datetime.now()
                y_pred = self._final_estimator.predict(X, **kwargs)
                predict_duration = (datetime.datetime.now() - predict_start_time).total_seconds()
                n = PhotonDataHelper.find_n(X)
                self.time_monitor['predict'].append((self.elements[-1][0], predict_duration, n))
                return y_pred
            else:
                return X
        else:
            return None

    def predict_proba(self, X, training: bool=False, **kwargs):
        if not training:
            X, _, kwargs = self.transform(X, y=None, **kwargs)

        if self._final_estimator is not None:
            if self._final_estimator.is_estimator:
                if hasattr(self._final_estimator, "predict_proba"):
                    if hasattr(self._final_estimator, 'needs_covariates'):
                        if self._final_estimator.needs_covariates:
                            return self._final_estimator.predict_proba(X, **kwargs)
                        else:
                            return self._final_estimator.predict_proba(X)
                    else:
                        return self._final_estimator.predict_proba(X)

        raise NotImplementedError("The final estimator does not have a predict_proba method")

    def inverse_transform(self, X, y=None, **kwargs):
        # simply use X to apply inverse_transform
        # does not work on any transformers changing y or kwargs!
        for name, transform in self.elements[::-1]:
            try:
                X, y, kwargs = transform.inverse_transform(X, y, **kwargs)
            except Exception as e:
                if isinstance(e, NotImplementedError):
                    return X, y, kwargs

        return X, y, kwargs

    def fit_transform(self, X, y=None, **kwargs):
        # return self.fit(X, y, **kwargs).transform(X, y, **kwargs)
        raise NotImplementedError('fit_transform not yet implemented in PHOTON Pipeline')

    def fit_predict(self, X, y=None, **kwargs):
        raise NotImplementedError('fit_predict not yet implemented in PHOTON Pipeline')

    @property
    def named_steps(self):
        return dict(self.elements)

    @property
    def _final_estimator(self):
        return self.elements[-1][1]

    @property
    def _estimator_type(self):
        return getattr(self._final_estimator, '_estimator_type')

    def clear_cache(self):
        if self.cache_man is not None:
            self.cache_man.clear_cache()

    def _add_preprocessing(self, preprocessing):
        if preprocessing:
            self.elements.insert(0, (preprocessing.name, preprocessing))

