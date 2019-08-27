from photonai.base.PhotonBase import Hyperpipe, PipelineElement, PipelineStack, PipelineBranch, SourceFilter, PipelineSwitch
from photonai.optimization.Hyperparameters import FloatRange, IntegerRange, Categorical
from photonai.configuration.Register import PhotonRegister
from sklearn.model_selection import KFold
from sklearn.datasets import load_breast_cancer
import numpy as np
from photonai.investigator.Investigator import Investigator


# LOAD DATA FROM SKLEARN
X, y = load_breast_cancer(True)

# CREATE HYPERPIPE
my_pipe = Hyperpipe('data_integration',
                    optimizer='grid_search',
                    metrics=['accuracy', 'precision', 'recall'],
                    best_config_metric='f1_score',
                    outer_cv=KFold(n_splits=5),
                    inner_cv=KFold(n_splits=5),
                    verbosity=1)
my_pipe += PipelineSwitch('PreprocessingSwitch', [PipelineElement('SimpleImputer'), PipelineElement('StandardScaler')])

# Use only "mean" features: [mean_radius, mean_texture, mean_perimeter, mean_area, mean_smoothness, mean_compactness,
# mean_concavity, mean_concave_points, mean_symmetry, mean_fractal_dimension
mean_branch = PipelineBranch('MeanFeature')
mean_branch += SourceFilter(indices=np.arange(10))
mean_branch += PipelineElement('SVC')

# Use only "error" features
error_branch = PipelineBranch('ErrorFeature')
error_branch += SourceFilter(indices=np.arange(10, 20))
error_branch += PipelineElement('SVC')

# use only "worst" features: [worst_radius, worst_texture, ..., worst_fractal_dimension]
worst_branch = PipelineBranch('WorstFeature')
worst_branch += SourceFilter(indices=np.arange(20, 30))
worst_branch += PipelineElement('SVC')

# voting = True to mean the result of every branch
my_pipe_stack = PipelineStack('SourceStack', voting=True)
my_pipe_stack += mean_branch
my_pipe_stack += error_branch
my_pipe_stack += worst_branch

my_pipe += my_pipe_stack

my_pipe += PipelineSwitch('EstimatorSwitch', [PipelineElement('RandomForestClassifier'), PipelineElement('SVC')])

my_pipe.fit(X, y)

Investigator.show(my_pipe)
debug = True

