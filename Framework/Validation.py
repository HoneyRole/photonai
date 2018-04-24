import time
import traceback
import warnings

# import matplotlib.pyplot as plt
import numpy as np

from Helpers.TFUtilities import one_hot_to_binary
from Logging.Logger import Logger
from .ResultLogging import FoldMetrics, FoldTupel, FoldOperations, Configuration, MasterElementType
from .ResultsDatabase import MDBInnerFold, MDBScoreInformation, MDBFoldMetric, MDBConfig, MDBHelper

class TestPipeline(object):

    def __init__(self, pipe, specific_config, metrics, mother_inner_fold_handle, raise_error=False):

        self.params = specific_config
        self.pipe = pipe
        self.metrics = metrics
        self.raise_error = raise_error
        self.mother_inner_fold_handle = mother_inner_fold_handle

    def calculate_cv_score(self, X, y, cv_iter, save_predictions=False):

        # needed for testing Timeboxed Random Grid Search
        # time.sleep(35)

        config_item = MDBConfig()
        config_item.inner_folds = []
        config_item.metrics_test = []
        config_item.metrics_train = []
        fold_cnt = 0

        inner_fold_list = []
        try:

            # do inner cv
            for train, test in cv_iter:

                    # set params to current config
                    self.pipe.set_params(**self.params)

                    # inform children in which inner fold we are
                    # self.pipe.distribute_cv_info_to_hyperpipe_children(inner_fold_counter=fold_cnt)
                    self.mother_inner_fold_handle(fold_cnt)

                    # start fitting
                    fit_start_time = time.time()
                    self.pipe.fit(X[train], y[train])

                    # Todo: Fit Process Metrics

                    # write down how long the fitting took
                    fit_duration = time.time()-fit_start_time
                    config_item.fit_duration_minutes = fit_duration

                    # score test data
                    curr_test_fold = TestPipeline.score(self.pipe, X[test], y[test], self.metrics, indices=test,
                                                        save_predictions=save_predictions)

                    # score train data
                    curr_train_fold = TestPipeline.score(self.pipe, X[train], y[train], self.metrics, indices=train,
                                                         save_predictions=save_predictions)

                    # fill result tree with fold information
                    inner_fold = MDBInnerFold()
                    inner_fold.fold_nr = fold_cnt
                    inner_fold.training = curr_train_fold
                    inner_fold.validation = curr_test_fold
                    #inner_fold.number_samples_training = int(len(train))
                    #inner_fold.number_samples_validation = int(len(test))
                    inner_fold_list.append(inner_fold)

                    fold_cnt += 1

            # calculate mean and std over all folds
            config_item.inner_folds = inner_fold_list
            config_item.metrics_train, config_item.metrics_test = MDBHelper.calculate_metrics(config_item,
                                                                                              self.metrics)

        except Exception as e:
            if self.raise_error:
                raise e
            Logger().error(e)
            traceback.print_exc()
            config_item.config_failed = True
            config_item.config_error = str(e)
            warnings.warn('One test iteration of pipeline failed with error')


        return config_item

    @staticmethod
    def score(estimator, X, y_true, metrics, indices=[], save_predictions=False):

        scoring_time_start = time.time()

        output_metrics = {}
        non_default_score_metrics = list(metrics)
        if 'score' in metrics:
            if hasattr(estimator, 'score'):
                # Todo: Here it is potentially slowing down!!!!!!!!!!!!!!!!
                default_score = estimator.score(X, y_true)
                output_metrics['score'] = default_score
                non_default_score_metrics.remove('score')

        y_pred = estimator.predict(X)

        f_importances = []
        if hasattr(estimator._final_estimator.base_element, 'coef_'):
            f_importances = estimator._final_estimator.base_element.coef_
            f_importances = f_importances.tolist()
        elif hasattr(estimator._final_estimator.base_element, 'feature_importances_'):
            f_importances = estimator._final_estimator.base_element.feature_importances_
            f_importances = f_importances.tolist()
        # Nice to have
        # TestPipeline.plot_some_data(y_true, y_pred)

        score_metrics = TestPipeline.calculate_metrics(y_true, y_pred, non_default_score_metrics)

        # add default metric
        if output_metrics:
            output_metrics = {**output_metrics, **score_metrics}
        else:
            output_metrics = score_metrics

        final_scoring_time = time.time() - scoring_time_start
        if save_predictions:
            score_result_object = MDBScoreInformation(metrics=output_metrics,
                                                        score_duration=final_scoring_time,
                                               y_pred=y_pred.tolist(), y_true=y_true.tolist(),
                                                      indices=np.asarray(indices).tolist(),
                                               feature_importances=f_importances)
        else:
            score_result_object = MDBScoreInformation(metrics=output_metrics,
                                                        score_duration=final_scoring_time)
        return score_result_object

    @staticmethod
    def calculate_metrics(y_true, y_pred, metrics):

        # Todo: HOW TO CHECK IF ITS REGRESSION?!
        # The following works only for classification
        # if np.ndim(y_pred) == 2:
        #     y_pred = one_hot_to_binary(y_pred)
        #     Logger().warn("test_predictions was one hot encoded => transformed to binary")
        #
        # if np.ndim(y_true) == 2:
        #     y_true = one_hot_to_binary(y_true)
        #     Logger().warn("test_y was one hot encoded => transformed to binary")

        output_metrics = {}
        if metrics:
            for metric in metrics:
                scorer = Scorer.create(metric)
                scorer_value = scorer(y_true, y_pred)
                output_metrics[metric] = scorer_value

        return output_metrics

    # @staticmethod
    # def plot_some_data(data, targets_true, targets_pred):
    #     ax_array = np.arange(0, data.shape[0], 1)
    #     plt.figure().clear()
    #     plt.plot(ax_array, data, ax_array, targets_true, ax_array, targets_pred)
    #     plt.title('A sample of data')
    #     plt.show()


class Scorer(object):

    ELEMENT_DICTIONARY = {
        # Classification
        'matthews_corrcoef': ('sklearn.metrics', 'matthews_corrcoef'),
        'confusion_matrix': ('sklearn.metrics', 'confusion_matrix'),
        'accuracy': ('sklearn.metrics', 'accuracy_score'),
        'f1_score': ('sklearn.metrics', 'f1_score'),
        'hamming_loss': ('sklearn.metrics', 'hamming_loss'),
        'log_loss': ('sklearn.metrics', 'log_loss'),
        'precision': ('sklearn.metrics', 'precision_score'),
        'recall': ('sklearn.metrics', 'recall_score'),
        # Regression
        'mean_squared_error': ('sklearn.metrics', 'mean_squared_error'),
        'mean_absolute_error': ('sklearn.metrics', 'mean_absolute_error'),
        'explained_variance': ('sklearn.metrics', 'explained_variance_score'),
        'r2': ('sklearn.metrics', 'r2_score'),
        'pearson_correlation': ('photon_core.Framework.Metrics', 'pearson_correlation'),
        'variance_explained':  ('photon_core.Framework.Metrics', 'variance_explained_score'),
        'categorical_accuracy': ('photon_core.Framework.Metrics','categorical_accuracy_score')
    }

    # def __init__(self, estimator, x, y_true, metrics):
    #     self.estimator = estimator
    #     self.x = x
    #     self.y_true = y_true
    #     self.metrics = metrics

    @classmethod
    def create(cls, metric):
        if metric in Scorer.ELEMENT_DICTIONARY:
            try:
                desired_class_info = Scorer.ELEMENT_DICTIONARY[metric]
                desired_class_home = desired_class_info[0]
                desired_class_name = desired_class_info[1]
                imported_module = __import__(desired_class_home, globals(),
                                             locals(), desired_class_name, 0)
                desired_class = getattr(imported_module, desired_class_name)
                scoring_method = desired_class
                return scoring_method
            except AttributeError as ae:
                Logger().error('ValueError: Could not find according class: '
                               + Scorer.ELEMENT_DICTIONARY[metric])
                raise ValueError('Could not find according class:',
                                 Scorer.ELEMENT_DICTIONARY[metric])
        else:
            Logger().error('NameError: Metric not supported right now:' + metric)
            raise NameError('Metric not supported right now:', metric)


class OptimizerMetric(object):

    def __init__(self, metric, pipeline_elements, other_metrics):
        self.metric = metric
        self.greater_is_better = None
        self.other_metrics = other_metrics
        self.set_optimizer_metric(pipeline_elements)

    def check_metrics(self):
        if self.other_metrics:
            if self.metric not in self.other_metrics:
                self.other_metrics.append(self.metric)
        # maybe there's a better solution to this
        else:
            self.other_metrics = [self.metric]
        return self.other_metrics

    def get_optimum_config(self, tested_configs):

        list_of_config_vals = []
        list_of_non_failed_configs = [conf for conf in tested_configs if not conf.config_failed]

        if len(list_of_non_failed_configs) == 0:
            raise Warning("No Configs found which did not fail.")
        try:
            for config in list_of_non_failed_configs:
                list_of_config_vals.append(MDBHelper.get_metric(config, FoldOperations.MEAN, self.metric, train=False))

            if self.greater_is_better:
                # max metric
                best_config_metric_nr = np.argmax(list_of_config_vals)
            else:
                # min metric
                best_config_metric_nr = np.argmin(list_of_config_vals)
            return list_of_non_failed_configs[best_config_metric_nr]
        except BaseException as e:
            Logger().error(str(e))

    def set_optimizer_metric(self, pipeline_elements):
        if isinstance(self.metric, str):
            if self.metric in Scorer.ELEMENT_DICTIONARY:
                # for now do a simple hack and set greater_is_better
                # by looking at error/score in metric name
                metric_name = Scorer.ELEMENT_DICTIONARY[self.metric][1]
                specifier = metric_name.split('_')[-1]
                if specifier == 'score':
                    self.greater_is_better = True
                elif specifier == 'error':
                    self.greater_is_better = False
                else:
                    # Todo: better error checking?
                    Logger().error('NameError: Metric not suitable for optimizer.')
                    raise NameError('Metric not suitable for optimizer.')
            else:
                Logger().error('NameError: Specify valid metric.')
                raise NameError('Specify valid metric.')
        else:
            # if no optimizer metric was chosen, use default scoring method
            self.metric = 'score'

            last_element = pipeline_elements[-1]
            if hasattr(last_element.base_element, '_estimator_type'):
                self.greater_is_better = True
            else:
                # Todo: better error checking?
                Logger().error('NotImplementedError: ' +
                               'Last pipeline element does not specify '+
                               'whether it is a classifier, regressor, transformer or '+
                               'clusterer.')
                raise NotImplementedError('Last pipeline element does not specify '
                                          'whether it is a classifier, regressor, transformer or '
                                          'clusterer.')
