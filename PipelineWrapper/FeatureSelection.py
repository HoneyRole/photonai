# Wrapper for Feature Selection (Select Percentile)

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import f_regression, f_classif, SelectPercentile, VarianceThreshold


class FRegressionSelectPercentile(BaseEstimator, TransformerMixin):
    _estimator_type = "transformer"

    def __init__(self, percentile=10):
        self.var_thres = VarianceThreshold()
        self.percentile = percentile
        self.my_fs = None

    def fit(self, X, y):
        X = self.var_thres.fit_transform(X)
        self.my_fs = SelectPercentile(score_func=f_regression, percentile=self.percentile)
        self.my_fs.fit(X,y)
        return self

    def transform(self, X):
        X = self.var_thres.transform(X)
        return self.my_fs.transform(X)

class FClassifSelectPercentile(BaseEstimator, TransformerMixin):
    _estimator_type = "transformer"

    def __init__(self, percentile=10):
        self.var_thres = VarianceThreshold()
        self.percentile = percentile
        self.my_fs = None

    def fit(self, X, y):
        X = self.var_thres.fit_transform(X)
        self.my_fs = SelectPercentile(score_func=f_classif, percentile=self.percentile)
        self.my_fs.fit(X,y)
        return self

    def transform(self, X):
        X = self.var_thres.transform(X)
        return self.my_fs.transform(X)

