import numpy as np

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import KFold

from photonai.base import Hyperpipe, PipelineElement, Preprocessing, OutputSettings
from photonai.optimization import FloatRange, Categorical, IntegerRange

# WE USE THE BREAST CANCER SET FROM SKLEARN
X, y = load_breast_cancer(True)

settings = OutputSettings(project_folder='./tmp/')

# DESIGN YOUR PIPELINE
my_pipe = Hyperpipe('basic_svm_pipe',  # the name of your pipeline
                    optimizer='sk_opt',  # which optimizer PHOTON shall use
                    optimizer_params={'n_configurations': 10},
                    metrics=['accuracy', 'precision', 'recall', 'balanced_accuracy'],  # the performance metrics of your interest
                    best_config_metric='accuracy',  # after hyperparameter search, the metric declares the winner config
                    outer_cv=KFold(n_splits=3),  # repeat hyperparameter search three times
                    inner_cv=KFold(n_splits=3),  # test each configuration ten times respectively,
                    verbosity=2,
                    output_settings=settings)


preprocessing = Preprocessing()
preprocessing += PipelineElement("LabelEncoder")

my_pipe += preprocessing

# ADD ELEMENTS TO YOUR PIPELINE
# first normalize all features
my_pipe.add(PipelineElement('StandardScaler'))
# then do feature selection using a PCA, specify which values to try in the hyperparameter search
my_pipe += PipelineElement('PCA', hyperparameters={'n_components': IntegerRange(5, 20)}, test_disabled=True)
# engage and optimize the good old SVM for Classification
my_pipe += PipelineElement('SVC', hyperparameters={'kernel': Categorical(['rbf', 'linear']),
                                                   'C': FloatRange(0.5, 2)}, gamma='scale')
# my_pipe += PipelineElement('LogisticRegression', hyperparameters={'penalty': ['l1', 'l2'], 'C': [0.5, 1]})


y = np.random.permutation(y)
# NOW TRAIN YOUR PIPELINE
my_pipe.fit(X, y)



#Investigator.show(my_pipe)
debug = True


