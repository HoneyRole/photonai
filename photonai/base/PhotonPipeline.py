from sklearn.utils.metaestimators import _BaseComposition


class PhotonPipeline(_BaseComposition):

    def __init__(self, steps):
        self.steps = steps

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
        return self._get_params('steps', deep=deep)

    def set_params(self, **kwargs):
        """Set the parameters of this estimator.
        Valid parameter keys can be listed with ``get_params()``.
        Returns
        -------
        self
        """
        self._set_params('steps', **kwargs)

        return self

    def _validate_steps(self):
        names, estimators = zip(*self.steps)

        # validate names
        self._validate_names(names)

        # validate estimators
        transformers = estimators[:-1]
        estimator = estimators[-1]

        for t in transformers:
            if t is None:
                continue
            if (not (hasattr(t, "fit") or hasattr(t, "fit_transform")) or not
            hasattr(t, "transform")):
                raise TypeError("All intermediate steps should be "
                                "transformers and implement fit and transform."
                                " '%s' (type %s) doesn't" % (t, type(t)))

        # We allow last estimator to be None as an identity transformation
        if estimator is not None and not hasattr(estimator, "fit"):
            raise TypeError("Last step of Pipeline should implement fit. "
                            "'%s' (type %s) doesn't"
                            % (estimator, type(estimator)))

    def stepwise_transform(self, transformer, X, y=None, **kwargs):

        # Case| transforms X | needs_y | needs_covariates
        # -------------------------------------------------------
        #   1         yes        no           no     = transform(X) -> returns Xt
        #   2         yes        yes          no     = transform(X, y) -> returns Xt, yt
        #   3         yes        yes          yes    = transform(X, y, kwargs) -> returns Xt, yt, kwargst
        #   4         yes        no           yes    = transform(X, kwargs) -> returns Xt, kwargst
        #   5         no      yes or no      yes or no      = NOT ALLOWED

        if transformer.needs_y:
            if transformer.needs_covariates:
                X, y, kwargs = transformer.transform(X, y, **kwargs)
            else:
                X, y = transformer.transform(X, y)
        elif transformer.needs_covariates:
            X, kwargs = transformer.transform(X, **kwargs)
        else:
            X = transformer.transform(X)

        return X, y, kwargs


    def fit(self, X, y=None, **kwargs):

        self._validate_steps()

        for (name, transformer) in self.steps[:-1]:
            transformer.fit(X, y, **kwargs)
            X, y, kwargs = self.stepwise_transform(transformer, X, y, **kwargs)

        if self._final_estimator is not None:
            self._final_estimator.fit(X, y, **kwargs)

        return self

    def transform(self, X, y=None, **kwargs):

        for (name, transformer) in self.steps[:-1]:
            X, y, kwargs = self.stepwise_transform(transformer, X, y, **kwargs)

        if self._final_estimator is not None:
            if hasattr(self._final_estimator, 'transform'):
                X, y, kwargs = self.stepwise_transform(self._final_estimator, X, y, **kwargs)
        return X


    def predict(self, X, y=None, **kwargs):
        for (name, transformer) in self.steps[:-1]:
            X, y, kwargs = self.stepwise_transform(transformer, X, y, **kwargs)

        if self._final_estimator is not None:
            if hasattr(self._final_estimator, 'predict'):
                y_pred = self._final_estimator.predict(X)
                return y_pred
        else:
            return None


    def inverse_transform(self, X, y, **kwargs):
        # simply use X to apply inverse_transform
        # does not work on any transformers changing or kwargs!
        Xt = X
        for name, transform in self.steps[::-1]:
            if hasattr(transform, 'inverse_transform'):
                Xt = transform.inverse_transform(Xt)
        return Xt

    def fit_transform(self, X, y=None, **kwargs):
        # return self.fit(X, y, **kwargs).transform(X, y, **kwargs)
        raise NotImplementedError('fit_transform not yet implemented in PHOTON Pipeline')

    def fit_predict(self, X, y=None, **kwargs):
        raise NotImplementedError('fit_predict not yet implemented in PHOTON Pipeline')

    def predict_proba(self, X):
        raise NotImplementedError('predict_proba not yet implemented in PHOTON Pipeline')



    @property
    def _estimator_type(self):
        return self.steps[-1][1]._estimator_type

    @property
    def named_steps(self):
        return dict(self.steps)

    @property
    def _final_estimator(self):
        return self.steps[-1][1]
