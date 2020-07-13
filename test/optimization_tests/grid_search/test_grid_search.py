import types
import unittest
from functools import reduce
import operator
from inspect import signature

from photonai.base import PipelineElement, Switch, Branch, Hyperpipe, OutputSettings
from photonai.optimization import GridSearchOptimizer, RandomGridSearchOptimizer, TimeBoxedRandomGridSearchOptimizer, \
    IntegerRange
from photonai.optimization.base_optimizer import PhotonBaseOptimizer, PhotonSlaveOptimizer, PhotonMasterOptimizer

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import KFold, ShuffleSplit


class GridSearchOptimizerTest(unittest.TestCase):

    def setUp(self):
        """
        Set up for GridSearchTest.
        """
        self.pipeline_elements = [PipelineElement("StandardScaler"),
                                  PipelineElement('PCA', hyperparameters={'n_components': IntegerRange(5, 20)}),
                                  PipelineElement("SVC")]
        self.optimizer = GridSearchOptimizer()
        self.optimizer_name = 'grid_search'

    def create_hyperpipe(self):
        self.hyperpipe = Hyperpipe('optimizer_test',
                                   output_settings=OutputSettings(project_folder='./tmp'),
                                   metrics=['accuracy'],
                                   best_config_metric='accuracy',
                                   inner_cv=KFold(n_splits=3),
                                   outer_cv=ShuffleSplit(n_splits=2),
                                   optimizer=self.optimizer_name)

    def test_run(self):
        self.create_hyperpipe()
        for p in self.pipeline_elements:
            self.hyperpipe += p
        X, y = load_breast_cancer(True)
        self.hyperpipe.fit(X, y)

    def test_all_functions_available(self):
        """
        Test existence of functions and parameters ->  .ask() .tell() .prepare()
        """
        self.assertTrue(hasattr(self.optimizer, 'prepare'))
        self.assertListEqual(list(signature(self.optimizer.prepare).parameters.keys()),
                             ['pipeline_elements', 'maximize_metric'])
        self.assertTrue(hasattr(self.optimizer, 'tell'))
        self.assertListEqual(list(signature(self.optimizer.tell).parameters.keys()), ['config', 'performance'])
        self.assertTrue(hasattr(self.optimizer, 'ask'))

    def test_all_attributes_available(self):
        """
        Test for .ask and .param_grid attribute. .ask is important for next configuration that should be tested.
        """
        self.optimizer.prepare(pipeline_elements=self.pipeline_elements, maximize_metric=True)
        self.assertIsInstance(self.optimizer.ask, types.GeneratorType)

    def test_ask(self):
        """
        Test general functionality of .ask()
        """
        self.optimizer.prepare(pipeline_elements=self.pipeline_elements, maximize_metric=True)
        ask_list = list(self.optimizer.ask)
        self.assertIsInstance(ask_list, list)
        self.assertSetEqual(set([str(type(a)) for a in ask_list]), set(["<class 'dict'>"]))
        generated_elements = reduce(operator.concat, [list(a.keys()) for a in ask_list])
        self.assertIn("PCA__n_components", generated_elements)
        return generated_elements

    def test_ask_advanced(self):
        """
        Test advanced functionality of .ask()
        """
        branch = Branch('branch')
        branch += PipelineElement('PCA')
        branch += PipelineElement('SVC', {'C': [0.1, 1], 'kernel': ['rbf', 'sigmoid']})
        pipe_switch = Switch('switch', [PipelineElement("StandardScaler"), PipelineElement("MaxAbsScaler")])
        self.pipeline_elements = [PipelineElement("StandardScaler"),
                                  PipelineElement('PCA', hyperparameters={'n_components': IntegerRange(5, 20)},
                                                  test_disabled=True),
                                  pipe_switch,
                                  branch,
                                  Switch('Switch_in_switch', [branch, pipe_switch])]
        generated_elements = self.test_ask()
        self.assertIn("PCA__n_components", generated_elements)
        self.assertIn("Switch_in_switch__current_element", generated_elements)
        self.assertIn("branch__SVC__C", generated_elements)
        self.assertIn("branch__SVC__kernel", generated_elements)
        self.assertIn("switch__current_element", generated_elements)


class RandomGridSearchOptimizerTest(GridSearchOptimizerTest):

    def setUp(self):
        """
        Set up for RandomGridSearchOptimizer.
        """
        self.pipeline_elements = [PipelineElement("StandardScaler"),
                                  PipelineElement('PCA', hyperparameters={'n_components': IntegerRange(5, 20)}),
                                  PipelineElement("SVC")]
        self.optimizer = RandomGridSearchOptimizer()
        self.optimizer_name = 'random_grid_search'

    def test_parameter_k(self):
        """
        Test for parameter k.
        """
        self.optimizer = RandomGridSearchOptimizer(n_configurations=3)
        self.optimizer.prepare(pipeline_elements=self.pipeline_elements, maximize_metric=True)
        self.assertEqual(len(self.optimizer.param_grid), 3)
        self.optimizer = RandomGridSearchOptimizer(n_configurations=500)
        self.optimizer.prepare(pipeline_elements=self.pipeline_elements, maximize_metric=True)
        self.assertEqual(len(self.optimizer.param_grid), 15)


class TimeBoxedRandomGridSearchOptimizerTest(RandomGridSearchOptimizerTest):

    def setUp(self):
        """
        Set up for TimeBoxedRandomGridSearchOptimizer
        """
        self.pipeline_elements = [PipelineElement("StandardScaler"),
                                  PipelineElement('PCA', hyperparameters={'n_components': IntegerRange(5, 20)}),
                                  PipelineElement("SVC")]
        self.optimizer = TimeBoxedRandomGridSearchOptimizer()
        self.optimizer_name = 'timeboxed_random_grid_search'


class BaseOptimizerTests(unittest.TestCase):

    def test_base_interface(self):
        opt = PhotonBaseOptimizer()
        opt.plot('/tmp')
        with self.assertRaises(NotImplementedError):
            opt.plot_objective()
        with self.assertRaises(NotImplementedError):
            opt.plot_evaluations()

    def test_slave_interface(self):
        opt = PhotonSlaveOptimizer()
        opt.prepare(list(), True)
        opt.ask()
        opt.tell(dict(), dict())

    def test_master_interface(self):
        opt = PhotonMasterOptimizer()
        opt.prepare(list(), True, None)
        opt.optimize()
