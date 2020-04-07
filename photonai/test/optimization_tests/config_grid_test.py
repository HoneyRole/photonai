import unittest

from sklearn.datasets import load_breast_cancer
from photonai.base import PipelineElement, Switch, Branch, Hyperpipe, OutputSettings, Stack
from photonai.optimization import IntegerRange, FloatRange
from photonai.optimization.config_grid import create_global_config_dict, create_global_config_grid
from photonai.test.photon_base_test import PhotonBaseTest

class CreateGlobalConfigBaseElements(unittest.TestCase):

    def setUp(self):
        self.scaler = PipelineElement('StandardScaler', test_disabled=True)
        self.pca = PipelineElement('PCA', {'n_components': IntegerRange(1, 3)})
        self.svc = PipelineElement('SVC', {'C': [0.1, 1], 'kernel': ['rbf', 'sigmoid']})
        self.rf = PipelineElement("RandomForestClassifier")  # no hyperparameter
        self.pipeline_elements = [self.scaler, self.pca, self.svc, self.rf]

    def create_global_config_one_element_test(self):
        """
        Test for function create_global_config_dict with one element in param pipeline_elements (:list)
        """
        # config dict
        self.assertDictEqual(create_global_config_dict([self.svc]), {'SVC__C': [0.1, 1],
                                                                     'SVC__kernel': ['rbf', 'sigmoid']})
        self.assertDictEqual(create_global_config_dict([self.scaler]), {'StandardScaler__disabled': [False, True]})
        self.assertDictEqual(create_global_config_dict([self.pca]), {'PCA__n_components': [1, 2]})
        self.assertDictEqual(create_global_config_dict([self.rf]), {})  # no hyperparameter

        # config grid
        self.assertListEqual(create_global_config_grid([self.svc]), [{'SVC__C': 0.1, 'SVC__kernel': 'rbf'},
                                                                     {'SVC__C': 0.1, 'SVC__kernel': 'sigmoid'},
                                                                     {'SVC__C': 1, 'SVC__kernel': 'rbf'},
                                                                     {'SVC__C': 1, 'SVC__kernel': 'sigmoid'}])
        self.assertListEqual(create_global_config_grid([self.scaler]), [{'StandardScaler__disabled': False},
                                                                        {'StandardScaler__disabled': True}])
        self.assertListEqual(create_global_config_grid([self.pca]), [{'PCA__n_components': 1},
                                                                     {'PCA__n_components': 2}])
        self.assertListEqual(create_global_config_grid([self.rf]), [{}])   # no hyperparameter

    def create_global_config_some_elements_test(self):
        """
        Test for function create_global_config_dict with three elements in param pipeline_elements (:list)

        case of two elements with same names are checked some structures above...
        """
        # config dict
        self.assertDictEqual(
            create_global_config_dict(self.pipeline_elements), {'StandardScaler__disabled': [False, True],
                                                                'PCA__n_components': [1, 2],
                                                                'SVC__C': [0.1, 1],
                                                                'SVC__kernel': ['rbf', 'sigmoid']})

        # config grid
        self.assertListEqual(
            create_global_config_grid(self.pipeline_elements),
            [{'StandardScaler__disabled': False, 'PCA__n_components': 1, 'SVC__C': 0.1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 1, 'SVC__C': 0.1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 1, 'SVC__C': 1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 1, 'SVC__C': 1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 2, 'SVC__C': 0.1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 2, 'SVC__C': 0.1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 2, 'SVC__C': 1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': False, 'PCA__n_components': 2, 'SVC__C': 1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 1, 'SVC__C': 0.1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 1, 'SVC__C': 0.1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 1, 'SVC__C': 1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 1, 'SVC__C': 1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 2, 'SVC__C': 0.1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 2, 'SVC__C': 0.1, 'SVC__kernel': 'sigmoid'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 2, 'SVC__C': 1, 'SVC__kernel': 'rbf'},
             {'StandardScaler__disabled': True, 'PCA__n_components': 2, 'SVC__C': 1, 'SVC__kernel': 'sigmoid'}])


class CreateGlobalConfigAdvancedElements(PhotonBaseTest):

    def setUp(self):
        self.svc_pipe_element = PipelineElement('SVC', {'C': [0.1, 1], 'kernel': ['rbf', 'sigmoid']})
        self.lr_pipe_element = PipelineElement('DecisionTreeClassifier', {'min_samples_split': [2, 3, 4]})
        self.pipe_switch = Switch('switch', [self.svc_pipe_element, self.lr_pipe_element])

        self.branch = Branch('branch')
        self.branch += PipelineElement('PCA')
        self.branch += self.svc_pipe_element

        self.switch_in_switch = Switch('Switch_in_switch', [self.branch,
                                                            self.pipe_switch])

    def create_global_config_switch_test(self):
        """
        assert number of different configs to test
        each config combi for each element: 4 for SVC and 3 for logistic regression = 7
        """
        self.assertEqual(len(self.pipe_switch.pipeline_element_configurations), 2)
        self.assertEqual(len(self.pipe_switch.pipeline_element_configurations[0]), 4)
        self.assertEqual(len(self.pipe_switch.pipeline_element_configurations[1]), 3)

        # config dict
        self.assertDictEqual(create_global_config_dict([self.pipe_switch]), {'switch__current_element': [(0, 0), (0, 1),
                                                                                                         (0, 2), (0, 3),
                                                                                                         (1, 0), (1, 1),
                                                                                                         (1, 2)]})
        # config grid
        self.assertListEqual(create_global_config_grid([self.pipe_switch]), [{'switch__current_element': (0, 0)},
                                                                             {'switch__current_element': (0, 1)},
                                                                             {'switch__current_element': (0, 2)},
                                                                             {'switch__current_element': (0, 3)},
                                                                             {'switch__current_element': (1, 0)},
                                                                             {'switch__current_element': (1, 1)},
                                                                             {'switch__current_element': (1, 2)}])

    def create_global_config_branch_test(self):
        """
        Test for function create_global_config_dict/grid with branch element.
        """
        # config dict
        self.assertDictEqual(create_global_config_dict([self.branch]), {'branch__SVC__C': [0.1, 1],
                                                                        'branch__SVC__kernel': ['rbf', 'sigmoid']})

        # config grid
        self.assertListEqual(
            create_global_config_grid([self.branch]), [{'branch__SVC__C': 0.1, 'branch__SVC__kernel': 'rbf'},
                                                       {'branch__SVC__C': 0.1, 'branch__SVC__kernel': 'sigmoid'},
                                                       {'branch__SVC__C': 1, 'branch__SVC__kernel': 'rbf'},
                                                       {'branch__SVC__C': 1, 'branch__SVC__kernel': 'sigmoid'}])

    def create_global_config_switch_in_swicht_test(self):
        """
        Test for function create_global_config_dict/grid with switch in switch.

        switch between branch with 4 hyperparameters and switch with 7 -> see above.
        """
        # config dict
        self.assertDictEqual(create_global_config_dict([self.switch_in_switch]),
                             {'Switch_in_switch__current_element': [(0, 0), (0, 1), (0, 2), (0, 3),
                                                                    (1, 0), (1, 1), (1, 2), (1, 3),
                                                                    (1, 4), (1, 5), (1, 6)]})

        # config grid
        self.assertListEqual(
            create_global_config_grid([self.switch_in_switch]), [{'Switch_in_switch__current_element': (0, 0)},
                                                                 {'Switch_in_switch__current_element': (0, 1)},
                                                                 {'Switch_in_switch__current_element': (0, 2)},
                                                                 {'Switch_in_switch__current_element': (0, 3)},
                                                                 {'Switch_in_switch__current_element': (1, 0)},
                                                                 {'Switch_in_switch__current_element': (1, 1)},
                                                                 {'Switch_in_switch__current_element': (1, 2)},
                                                                 {'Switch_in_switch__current_element': (1, 3)},
                                                                 {'Switch_in_switch__current_element': (1, 4)},
                                                                 {'Switch_in_switch__current_element': (1, 5)},
                                                                 {'Switch_in_switch__current_element': (1, 6)}])

    def test_huge_combinations(self):
        hp = Hyperpipe('huge_combinations', metrics=['accuracy'], best_config_metric='accuracy',
                       output_settings=OutputSettings(project_folder=self.tmp_folder_path))

        hp += PipelineElement("PCA", hyperparameters={'n_components': [5, 10]})
        stack = Stack('ensemble')
        for i in range(20):
            stack += PipelineElement('SVC', hyperparameters={'C': FloatRange(0.001, 5),
                                                             'kernel': ["linear", "rbf", "sigmoid", "polynomial"]})
        hp += stack
        hp += PipelineElement("SVC", hyperparameters={'kernel': ["linear", "rbf", "sigmoid"]})
        X, y = load_breast_cancer(True)
        with self.assertRaises(Warning):
            hp.fit(X, y)
