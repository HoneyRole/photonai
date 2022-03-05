import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from photonai.photonlogger.logger import logger

try:
    from imblearn import over_sampling, under_sampling, combine
    __found__ = True
except ModuleNotFoundError:
    __found__ = False


class ImbalancedDataTransformer(BaseEstimator, TransformerMixin):
    """
    Applies the chosen strategy to the data in order to balance the input data.
    Instantiates the strategy filter object according to the name given as string literal.
    Underlying architecture: Imbalanced-Learning.
    More information on their [documentation](https://imbalanced-learn.org/stable/).

    Example:
        ``` python
        from photonai.optimization import Categorical

        tested_methods = Categorical(['RandomOverSampler', 'SMOTEENN', 'SVMSMOTE',
                              'BorderlineSMOTE', 'SMOTE', 'ClusterCentroids'])
        PipelineElement('ImbalancedDataTransformer',
                        hyperparameters={'method_name': tested_methods},
                        test_disabled=True)
        ```

    """
    IMBALANCED_DICT = {
        'oversampling': ["ADASYN",
                         "BorderlineSMOTE",
                         "KMeansSMOTE",
                         "RandomOverSampler",
                         "SMOTE",
                         "SMOTENC",
                         "SVMSMOTE"],
        'undersampling': ["AllKNN",
                          "ClusterCentroids",
                          "CondensedNearestNeighbour",
                          "EditedNearestNeighbours",
                          "InstanceHardnessThreshold",
                          "NearMiss",
                          "NeighbourhoodCleaningRule",
                          "OneSidedSelection",
                          "TomekLinks",
                          "RandomUnderSampler",
                          "RepeatedEditedNearestNeighbours"],
        'combine': ["SMOTEENN", "SMOTETomek"],
    }

    def __init__(self, method_name: str = 'RandomUnderSampler', config: dict = None):
        """
        Instantiates an object that transforms the data into balanced groups according to the given method.

        Parameters:
            method_name:
                Imbalanced learning strategy. Possible values with

                - an oversampling strategy are:
                    - ADASYN,
                    - BorderlineSMOTE,
                    - KMeansSMOTE,
                    - RandomOverSampler,
                    - SMOTE,
                    - SMOTENC,
                    - SVMSMOTE,

                - an undersampling strategy are:
                    - ClusterCentroids,
                    - RandomUnderSampler,
                    - NearMiss,
                    - InstanceHardnessThreshold,
                    - CondensedNearestNeighbour,
                    - EditedNearestNeighbours,
                    - RepeatedEditedNearestNeighbours,
                    - AllKNN,
                    - NeighbourhoodCleaningRule,
                    - OneSidedSelection,

                - a combined strategy are:
                    - SMOTEENN,
                    - SMOTETomek.

            config:
                Each strategy has a set of presets. This parameter is necessary
                to select the appropriate settings for the selected method.
                It is important that the key exactly matches the method_name.
                If no key is found for a method, it will be started with the default settings.
                Please do not use this parameter inside the 'hyperparmeters' to optimize it.

        """
        if not __found__:
            raise ModuleNotFoundError("Module imblearn not found or not installed as expected. "
                                      "Please install the requirements.txt in PHOTON main folder.")

        self.config = config
        self._method_name = None
        self.method_name = method_name
        self.needs_y = True

    @property
    def method_name(self):
        return self._method_name

    @method_name.setter
    def method_name(self, value):

        imbalance_type = ''
        for group, possible_strategies in ImbalancedDataTransformer.IMBALANCED_DICT.items():
            if value in possible_strategies:
                imbalance_type = group

        if imbalance_type == "oversampling":
            home = over_sampling
        elif imbalance_type == "undersampling":
            home = under_sampling
        elif imbalance_type == "combine" or imbalance_type == "combination":
            home = combine
        else:
            msg = "Imbalance Type not found. Can be oversampling, undersampling or combine. " \
                  "Oversampling: method_name one of {}. Undersampling: method_name one of {}." \
                  "Combine: method_name one of {}.".format(str(self.IMBALANCED_DICT["oversampling"]),
                                                           str(self.IMBALANCED_DICT["undersampling"]),
                                                           str(self.IMBALANCED_DICT["combine"]))
            logger.error(msg)
            raise ValueError(msg)

        desired_class = getattr(home, value)
        self._method_name = value
        if self.config is not None and value in self.config:
            if not isinstance(self.config[value], dict):
                msg = "Please use for the imbalanced config a format like: " \
                      "config={'SMOTE': {'sampling_strategy': {0: 9, 1: 12}}}."
                logger.error(msg)
                raise ValueError(msg)
            self.method = desired_class(**self.config[value])
        else:
            self.method = desired_class()

    def fit_transform(self, X: np.ndarray, y: np.ndarray = None, **kwargs) -> (np.ndarray, np.ndarray):
        """
        Call of the underlying imblearn.fit_resample(X, y).

        Parameters:
            X:
                The input samples of shape [n_samples, n_features].

            y:
                The input targets of shape [n_samples, 1].

            **kwargs:
                Ignored input.

        Returns:
            Transformed data.

        """
        return self.method.fit_resample(X, y)

    #  define an alias for imblearn consistency
    fit_sample = fit_transform
    fit_resample = fit_transform

    def fit(self, X, y, **kwargs):
        """Empty method required in PHOTONAI."""
        return

    def transform(self, X: np.ndarray, y: np.ndarray = None, **kwargs) -> (np.ndarray, np.ndarray):
        """
        Forwarding to the self.fit_transform method.

        Parameters:
            X:
                The input samples of shape [n_samples, n_features].

            y:
                The input targets of shape [n_samples, 1].

            **kwargs:
                Ignored input.

        Returns:
            Transformed data.

        """
        return self.fit_transform(X, y)
