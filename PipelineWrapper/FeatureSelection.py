# Wrapper for Feature Selection (Select Percentile)
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import f_regression, f_classif, SelectPercentile, \
    VarianceThreshold, mutual_info_classif, mutual_info_regression, SelectKBest, chi2
from scipy.stats import pearsonr, f_oneway
from sklearn.decomposition import PCA, RandomizedPCA, IncrementalPCA
from hashlib import sha1
from pathlib import Path
import statsmodels.api as sm
import multiprocessing
from ..Logging.Logger import Logger

class PearsonFeatureSelector(BaseEstimator, TransformerMixin):
    _estimator_type = "transformer"

    def __init__(self, p_threshold=.05):
        self.p_threshold = p_threshold
        self.selected_indices = []

    def fit(self, X, y):

        # corr_coef = []
        corr_p = []

        for i in range(X.shape[1]):
            feature = X[:, i]
            corr = pearsonr(feature, y)
            # corr_coef.append(corr[0])
            corr_p.append(corr[1])

        # corr_coef = np.array(corr_coef)
        corr_p = np.array(corr_p)
        self.selected_indices = np.where((corr_p <= self.p_threshold))[0]
        return self

    def transform(self, X):
        selected_features = X[:, self.selected_indices]
        return selected_features


class FRegressionFilterPValue(BaseEstimator, TransformerMixin):
    _estimator_type = "transformer"

    def __init__(self, p_threshold=.05):
        self.p_threshold = p_threshold
        self.selected_indices = []

    def fit(self, X, y):
        f_values, p_values = f_regression(X, y)
        self.selected_indices = np.where(p_values < self.p_threshold)
        return self

    def transform(self, X):
        return X[:, self.selected_indices]

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


class AnovaSelectPercentile(BaseEstimator, TransformerMixin):
    _estimator_type = "transformer"

    def __init__(self, percentile=10):
        self.var_thres = VarianceThreshold()
        self.percentile = percentile
        self.my_fs = None

    def loc_anova(self, data, targets):
        fs = []
        ps = []
        for snpInd in range(data.shape[1]):
            a = targets[data[:, snpInd] == 1]
            b = targets[data[:, snpInd] == 2]
            c = targets[data[:, snpInd] == 3]
            f, p = f_oneway(a, b, c)
            fs.append(f)
            ps.append(p)

    def fit(self, X, y):
        X = self.var_thres.fit_transform(X)
        self.my_fs = SelectPercentile(score_func=self.loc_anova, percentile=self.percentile)
        self.my_fs.fit(X, y)
        return self

    def transform(self, X):
        X = self.var_thres.transform(X)
        return self.my_fs.transform(X)


class AnovaSelectPercentile(BaseEstimator, TransformerMixin):
    _estimator_type = "transformer"

    def __init__(self, percentile=10):
        # self.var_thres = VarianceThreshold()
        self.percentile = percentile
        self.my_fs = None

    def loc_anova(self, data, targets):
        fs = []
        ps = []
        for feature_ind in range(data.shape[1]):
            group_data = []
            uni_targets = np.unique(data[:, feature_ind])
            for feature_cat in uni_targets:
                group_data.append(targets[data[:, feature_ind] == feature_cat])
            f, p = f_oneway(*group_data)
            fs.append(f)
            ps.append(p)
        return fs, ps

    def inverse_transform(self, X):
        return self.my_fs.inverse_transform(X)

    def fit(self, X, y):
        # X = self.var_thres.fit_transform(X)
        self.my_fs = SelectPercentile(score_func=self.loc_anova, percentile=self.percentile)
        self.my_fs.fit(X, y)
        return self

    def transform(self, X):
        # X = self.var_thres.transform(X)
        return_values = self.my_fs.transform(X)
        if return_values.size == 0:
            return_values = np.zeros(X.shape)
        return return_values


class MIClassifSelectPercentile(BaseEstimator, TransformerMixin):
    _estimator_type = 'transformer'

    def __init__(self, percentile=10):
        self.var_thres = VarianceThreshold()
        self.percentile = percentile
        self.my_fs = None

    def fit(self, X, y):
        X = self.var_thres.fit_transform(X)
        self.my_fs = SelectPercentile(score_func=mutual_info_classif, percentile=self.percentile)
        self.my_fs.fit(X, y)
        return self

    def transform(self, X):
        X = self.var_thres.transform(X)
        return self.my_fs.transform(X)


class MIRegressionSelectPercentile(BaseEstimator, TransformerMixin):
    _estimator_type = 'transformer'

    def __init__(self, percentile=10):
        self.var_thres = VarianceThreshold()
        self.percentile = percentile
        self.my_fs = None

    def fit(self, X, y):
        X = self.var_thres.fit_transform(X)
        self.my_fs = SelectPercentile(score_func=mutual_info_regression, percentile=self.percentile)
        self.my_fs.fit(X, y)
        return self

    def transform(self, X):
        X = self.var_thres.transform(X)
        return self.my_fs.transform(X)

class Chi2KBest(BaseEstimator, TransformerMixin):
    _estimator_type = 'transformer'

    def __init__(self, k=10):
        self.var_thres = VarianceThreshold()
        self.k = k
        self.my_fs = None

    def fit(self, X, y):
        X = self.var_thres.fit_transform(X)
        self.my_fs = SelectKBest(score_func=chi2, k=self.k)
        self.my_fs.fit(X, y)
        return self

    def transform(self, X):
        X = self.var_thres.transform(X)
        return self.my_fs.transform(X)


class LogisticGWASFeatureSelection(BaseEstimator,TransformerMixin):
    _estimator_type = 'transformer'

    def __init__(self, p_thres=0.01, incremental_pca=0, logs='', n_pca_components=4, n_cores=1):
        self.pca = None
        self._y = None
        self.components = None
        self.ps = None

        self.n_pca_comp = n_pca_components
        self.n_cores = n_cores
        self.logs = logs
        self.incremental_pca = incremental_pca
        self.p_thres = p_thres


    def fit(self, X, y):
        self._y = y
        hash = sha1(np.asarray(X)).hexdigest()
        hash_file = Path(str(self.logs + '/' + hash + '.txt'))
        if hash_file.is_file():
            Logger().debug('Reloading GWAS p-values...')
            self.ps = np.loadtxt(self.logs + '/' + hash + '.txt')

        else:
            if self.incremental_pca:
                self.pca = IncrementalPCA(self.n_pca_comp, self.incremental_pca)
            else:
                self.pca = PCA(self.n_pca_comp)
            self.components = self.pca.fit_transform(X)
            params = zip(np.arange(0,X.shape[1]),np.nditer(X, flags = ['external_loop'], order = 'F'))
            pool = multiprocessing.Pool(self.n_cores)
            res = pool.map(self.parallelized_logistic_regression, params)
            pool.close()
            self.ps = np.asarray(res)
            self.ps[np.isnan(self.ps)] = 1
            np.savetxt(str(self.logs + '/' + hash + '.txt'), self.ps)
        return self

    def transform(self, X):
        X_selected = X[:,self.ps <= self.p_thres]
        Logger().debug('Remaining features after GWAS feature selection: {}'.format(X_selected.shape[1]))
        return X_selected

    def parallelized_logistic_regression(self, params):
        i, x = params
        if ((i+1) % 10000) == 0:
            Logger().debug('Running GWAS Feature Selection...done with {} SNPs.'.format(i+1))
        exog = np.concatenate([np.reshape(x, (x.shape[0], 1)), self.components], axis=1)
        exog = sm.add_constant(exog)
        logit_mod = sm.Logit(self._y, exog)
        try:
            logit_res = logit_mod.fit(disp=0)
            return logit_res.pvalues[1]
        except:
            return 1



