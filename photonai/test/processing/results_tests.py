import os
import unittest
from shutil import rmtree

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.datasets import load_boston
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold

from photonai.base import Hyperpipe, PipelineElement, OutputSettings
from photonai.optimization import IntegerRange, FloatRange, Categorical


class XPredictor(BaseEstimator, ClassifierMixin):

    _estimator_type = 'classifier'

    def __init__(self, change_predictions = False):
        self.needs_y = False
        self.needs_covariates = False
        self.change_predictions = change_predictions
        pass

    def fit(self, X, y=None, **kwargs):
        return self

    def predict(self, X, **kwargs):
        if self.change_predictions:
            # change it relative to value so that it is fold-specific
            return XPredictor.adapt_X(X)
        return X

    @staticmethod
    def adapt_X(X):
        return [i-(0.1*i) for i in X]

    def predict_proba(self, X):
        return X/10


class ResultHandlerAndHelperTests(unittest.TestCase):

    def setUp(self):

        self.inner_fold_nr = 10
        self.outer_fold_nr = 5
        
        self.y_true = np.linspace(1, 100, 100)
        self.X = self.y_true
        
        self.hyperpipe = Hyperpipe('test_prediction_collection',
                                   inner_cv=KFold(n_splits=self.inner_fold_nr),
                                   outer_cv=KFold(n_splits=self.outer_fold_nr),
                                   metrics=['mean_absolute_error', 'mean_squared_error'],
                                   best_config_metric='mean_absolute_error',
                                   output_settings=OutputSettings(save_predictions='all',
                                                                  project_folder='./tmp'))

    def tearDown(self):
        rmtree('./tmp/', ignore_errors=True)

    def test_cv_config_and_dummy_nr(self):
        X, y = load_boston(True)
        self.hyperpipe += PipelineElement('StandardScaler')
        self.hyperpipe += PipelineElement('PCA', {'n_components': IntegerRange(3, 7)})
        self.hyperpipe += PipelineElement('SVR', {'C': FloatRange(0.001, 10, num=10),
                                                  'kernel': Categorical(['linear', 'rbf'])})

        self.hyperpipe.fit(X, y)

        expected_configs = 4 * 10 * 2

        # check nr of outer and inner folds
        self.assertTrue(len(self.hyperpipe.results.outer_folds) == self.outer_fold_nr)
        self.assertTrue(len(self.hyperpipe.cross_validation.outer_folds) == self.outer_fold_nr)

        for outer_fold_id, inner_folds in self.hyperpipe.cross_validation.inner_folds.items():
            self.assertTrue(len(inner_folds) == self.inner_fold_nr)

        for outer_fold_result in self.hyperpipe.results.outer_folds:
            # check that we have the right amount of configs tested in each outer fold
            self.assertTrue(len(outer_fold_result.tested_config_list) == expected_configs)

            for config_result in outer_fold_result.tested_config_list:
                # check that we have the right amount of inner-folds per config
                self.assertTrue(len(config_result.inner_folds) == self.inner_fold_nr)

        self.check_for_dummy()

    def check_for_dummy(self):
        self.assertTrue(hasattr(self.hyperpipe.results, 'dummy_estimator'))
        # we should have mean and std for each metric respectively
        expected_dummy_metrics = len(self.hyperpipe.optimization.metrics) * 2
        if self.hyperpipe.cross_validation.eval_final_performance:
            self.assertTrue(len(self.hyperpipe.results.dummy_estimator.test) == expected_dummy_metrics)
        # we should have mean and std for each metric respectively
        self.assertTrue(len(self.hyperpipe.results.dummy_estimator.train) == expected_dummy_metrics)

    def test_get_predictions(self):

        self.hyperpipe += PipelineElement('PhotonTestXPredictor')
        self.hyperpipe.fit(self.X, self.y_true)

        inner_preds_received = self.hyperpipe.results_handler.get_validation_predictions()
        first_outer_fold_info = next(iter(self.hyperpipe.cross_validation.outer_folds.values()))
        values_to_expect = np.asarray(first_outer_fold_info.train_indices) + 1.0
        self.assertTrue(np.array_equal(inner_preds_received['y_pred'], values_to_expect))
        self.assertTrue(np.array_equal(inner_preds_received['y_true'], values_to_expect))
        self.assertTrue(np.array_equal(inner_preds_received['probabilities'], values_to_expect / 10))

        outer_preds_received = self.hyperpipe.results_handler.get_test_predictions()
        self.assertTrue(np.array_equal(outer_preds_received['y_pred'], self.y_true))
        self.assertTrue(np.array_equal(outer_preds_received['y_true'], self.y_true))
        self.assertTrue(np.array_equal(outer_preds_received['probabilities'], self.y_true / 10))

        csv_file = pd.read_csv(
            os.path.join(self.hyperpipe.output_settings.results_folder, 'best_config_predictions.csv'))
        self.assertTrue(np.array_equal(csv_file.y_pred.values, self.y_true))
        self.assertTrue(np.array_equal(csv_file.y_true.values, self.y_true))
        self.assertTrue(np.array_equal(csv_file.probabilities.values, self.y_true / 10))

    def test_get_predictions_no_outer_cv_eval_final_performance_false(self):
        self.hyperpipe += PipelineElement('PhotonTestXPredictor')
        self.hyperpipe.cross_validation.outer_cv = None
        self.hyperpipe.cross_validation.eval_final_performance = False
        self.hyperpipe.fit(self.X, self.y_true)
        self.check_predictions_eval_final_performance_false()

    def get_predictions_outer_cv_eval_final_performance_false(self):
        self.hyperpipe += PipelineElement('PhotonTestXPredictor')
        self.hyperpipe.cross_validation.eval_final_performance = False
        self.hyperpipe.fit(self.X, self.y_true)
        self.check_predictions_eval_final_performance_false()

    def check_predictions_eval_final_performance_false(self):
        inner_preds_received = self.hyperpipe.results_handler.get_validation_predictions()
        first_outer_fold_info = next(iter(self.hyperpipe.cross_validation.outer_folds.values()))
        values_to_expect = np.asarray(first_outer_fold_info.train_indices) + 1.0
        self.assertTrue(np.array_equal(inner_preds_received['y_pred'], values_to_expect))
        self.assertTrue(np.array_equal(inner_preds_received['y_true'], values_to_expect))
        self.assertTrue(np.array_equal(inner_preds_received['probabilities'], values_to_expect / 10))

        # we are not allowed to evalute the outer_folds test set so we get empty lists here
        outer_fold_predictiosn_received = self.hyperpipe.results_handler.get_test_predictions()
        self.assertTrue(len(outer_fold_predictiosn_received['y_pred']) == 0)
        self.assertTrue(len(outer_fold_predictiosn_received['y_true']) == 0)

        # in case we have no outer cv, we write the inner_cv predictions
        csv_file = pd.read_csv(
            os.path.join(self.hyperpipe.output_settings.results_folder, 'best_config_predictions.csv'))
        self.assertTrue(np.array_equal(csv_file.y_pred.values, values_to_expect))
        self.assertTrue(np.array_equal(csv_file.y_true.values, values_to_expect))
        self.assertTrue(np.array_equal(csv_file.probabilities.values, values_to_expect / 10))

    def test_best_config_stays_the_same(self):
        X, y = load_boston(True)
        self.hyperpipe += PipelineElement('StandardScaler')
        self.hyperpipe += PipelineElement('PCA', {'n_components': [4, 5]}, random_state=42)
        self.hyperpipe += PipelineElement('LinearRegression')
        self.hyperpipe.fit(X, y)

        best_config = self.hyperpipe.results.best_config.config_dict
        expected_best_config = {'PCA__n_components': 5}
        self.assertDictEqual(best_config, expected_best_config)

    def test_metrics_and_aggregations(self):
        
        self.hyperpipe += PipelineElement('PhotonTestXPredictor', change_predictions=True)
        X = np.linspace(0, 99, 100)
        y_true = X
        self.hyperpipe.fit(X, y_true)

        self.metric_assertions()
        self.check_for_dummy()

    def test_metrics_and_aggreation_eval_performance_false(self):
        self.hyperpipe = Hyperpipe('test_prediction_collection',
                                   inner_cv=KFold(n_splits=self.inner_fold_nr),
                                   metrics=['mean_absolute_error', 'mean_squared_error'],
                                   eval_final_performance=False,
                                   best_config_metric='mean_absolute_error',
                                   output_settings=OutputSettings(save_predictions='all',
                                                                  project_folder='./tmp'))

        self.test_metrics_and_aggregations()

    def test_metrics_and_aggregations_no_outer_cv_but_eval_performance_true(self):
        self.hyperpipe = Hyperpipe('test_prediction_collection',
                                   outer_cv=KFold(n_splits=self.outer_fold_nr),
                                   inner_cv=KFold(n_splits=self.inner_fold_nr),
                                   metrics=['mean_absolute_error', 'mean_squared_error'],
                                   eval_final_performance=False,
                                   best_config_metric='mean_absolute_error',
                                   output_settings=OutputSettings(save_predictions='all',
                                                                  project_folder='./tmp'))

        self.test_metrics_and_aggregations()

    def metric_assertions(self):
        def check_metrics(metric_name, expected_metric_list, mean_metrics):
            for metric in mean_metrics:
                if metric.metric_name == metric_name:
                    if metric.operation == 'FoldOperations.MEAN':
                        expected_val_mean = np.mean(expected_metric_list)
                        self.assertEqual(expected_val_mean, metric.value)
                    elif metric.operation == 'FoldOperations.STD':
                        expected_val_std = np.std(expected_metric_list)
                        self.assertAlmostEqual(expected_val_std, metric.value)
            return expected_val_mean, expected_val_std

        outer_collection = {'train': list(), 'test': list()}
        for i, (_, outer_fold) in enumerate(self.hyperpipe.cross_validation.outer_folds.items()):
            outer_fold_results = self.hyperpipe.results.outer_folds[i]
            config = outer_fold_results.tested_config_list[0]
            inner_fold_results = config.inner_folds

            inner_fold_metrics = {'train': list(), 'test': list()}
            for _, inner_fold in self.hyperpipe.cross_validation.inner_folds[outer_fold.fold_id].items():
                tree_result = inner_fold_results[inner_fold.fold_nr - 1]

                global_test_indices = outer_fold.train_indices[inner_fold.test_indices]
                expected_test_mae = mean_absolute_error(XPredictor.adapt_X(global_test_indices),
                                                        global_test_indices)
                inner_fold_metrics['test'].append(expected_test_mae)
                self.assertEqual(expected_test_mae, tree_result.validation.metrics['mean_absolute_error'])
                self.assertTrue(np.array_equal(tree_result.validation.indices, inner_fold.test_indices))
                self.assertEqual(len(global_test_indices), len(tree_result.validation.y_true))
                self.assertEqual(len(global_test_indices), len(tree_result.validation.y_pred))

                global_train_indices = outer_fold.train_indices[inner_fold.train_indices]
                expected_train_mae = mean_absolute_error(XPredictor.adapt_X(global_train_indices),
                                                         global_train_indices)
                inner_fold_metrics['train'].append(expected_train_mae)
                self.assertEqual(expected_train_mae, tree_result.training.metrics['mean_absolute_error'])
                # check that indices are as expected and the right number of y_pred and y_true exist in the tree
                self.assertTrue(np.array_equal(tree_result.training.indices, inner_fold.train_indices))
                self.assertEqual(len(global_train_indices), len(tree_result.training.y_true))
                self.assertEqual(len(global_train_indices), len(tree_result.training.y_pred))

                # get expected train and test mean and std respectively and calculate mean and std again.

            check_metrics('mean_absolute_error', inner_fold_metrics['train'], config.metrics_train)
            check_metrics('mean_absolute_error', inner_fold_metrics['test'], config.metrics_test)

            if self.hyperpipe.cross_validation.eval_final_performance:
                expected_outer_test_mae = mean_absolute_error(XPredictor.adapt_X(outer_fold.test_indices),
                                                              outer_fold.test_indices)

                self.assertTrue(np.array_equal(outer_fold_results.best_config.best_config_score.validation.indices,
                                         outer_fold.test_indices))
                self.assertEqual(len(outer_fold.test_indices),
                                 len(outer_fold_results.best_config.best_config_score.validation.y_true))
                self.assertEqual(len(outer_fold.test_indices),
                                 len(outer_fold_results.best_config.best_config_score.validation.y_pred))

                # check that indices are as expected and the right number of y_pred and y_true exist in the tree
                self.assertTrue(np.array_equal(outer_fold_results.best_config.best_config_score.training.indices,
                                               outer_fold.train_indices))
                self.assertEqual(len(outer_fold.train_indices),
                                 len(outer_fold_results.best_config.best_config_score.training.y_true))
                self.assertEqual(len(outer_fold.train_indices),
                                 len(outer_fold_results.best_config.best_config_score.training.y_pred))
            else:
                # if we dont use the test set, we want the values from the inner_cv to be copied
                expected_outer_test_mae = [m.value for m in outer_fold_results.best_config.metrics_test
                                           if m.metric_name == 'mean_absolute_error'
                                           and m.operation == 'FoldOperations.MEAN']
                if len(expected_outer_test_mae) > 0:
                    expected_outer_test_mae = expected_outer_test_mae[0]

                self.assertTrue(outer_fold_results.best_config.best_config_score.validation.metrics_copied_from_inner)
                self.assertTrue(outer_fold_results.best_config.best_config_score.training.metrics_copied_from_inner)

            outer_collection['test'].append(expected_outer_test_mae)
            self.assertEqual(outer_fold_results.best_config.best_config_score.validation.metrics['mean_absolute_error'],
                             expected_outer_test_mae)

            expected_outer_train_mae = mean_absolute_error(XPredictor.adapt_X(outer_fold.train_indices),
                                                           outer_fold.train_indices)
            outer_collection['train'].append(expected_outer_train_mae)
            self.assertAlmostEqual(outer_fold_results.best_config.best_config_score.training.metrics['mean_absolute_error'],
                                   expected_outer_train_mae)

        # check again in overall best config attribute
        check_metrics('mean_absolute_error', outer_collection['train'],
                      self.hyperpipe.results.metrics_train)

        check_metrics('mean_absolute_error', outer_collection['test'],
                      self.hyperpipe.results.metrics_test)

        # check if those agree with helper function output
        outer_fold_performances = self.hyperpipe.results_handler.get_performance_outer_folds()
        self.assertListEqual(outer_fold_performances['mean_absolute_error'], outer_collection['test'])

