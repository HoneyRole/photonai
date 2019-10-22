from sklearn.datasets import load_boston
from sklearn.model_selection import KFold

from photonai.base import Hyperpipe, PipelineElement, OutputSettings, Switch
from photonai.investigator import Investigator


# WE USE THE BREAST CANCER SET FROM SKLEARN
X, y = load_boston(True)

settings = OutputSettings(project_folder='./tmp/')

# DESIGN YOUR PIPELINE
my_pipe = Hyperpipe('feature_selection',  # the name of your pipeline
                    optimizer='grid_search',  # which optimizer PHOTON shall use
                    metrics=['mean_squared_error', 'pearson_correlation', 'mean_absolute_error', 'explained_variance'],
                    # the performance metrics of your interest
                    best_config_metric='mean_squared_error',  # after hyperparameter search, the metric declares the winner config
                    outer_cv=KFold(n_splits=3),  # repeat hyperparameter search three times
                    inner_cv=KFold(n_splits=3),  # test each configuration ten times respectively
                    verbosity=1,
                    output_settings=settings)

# ADD ELEMENTS TO YOUR PIPELINE
# first normalize all features
my_pipe += PipelineElement('StandardScaler')

lasso = PipelineElement('LassoFeatureSelection', hyperparameters={'percentile_to_keep': [0.1, 0.2, 0.3], 'alpha': 1})
f_regression = PipelineElement('FRegressionSelectPercentile', hyperparameters={'percentile': [10, 20, 30]})
my_pipe += Switch('FeatureSelection', [lasso, f_regression])

# engage and optimize the good old SVM for Classification
my_pipe += PipelineElement('RandomForestRegressor', hyperparameters={'n_estimators':[10]})


# NOW TRAIN YOUR PIPELINE
my_pipe.fit(X, y)

# AND SHOW THE RESULTS IN THE WEBBASED PHOTON INVESTIGATOR TOOL
Investigator.show(my_pipe)

# YOU CAN ALSO SAVE THE BEST PERFORMING PIPELINE FOR FURTHER USE
# my_pipe.save_optimum_pipe('/home/photon_user/photon_test/optimum_pipe.photon')

# YOU CAN ALSO LOAD YOUR RESULTS FROM THE MONGO DB
# Investigator.load_from_db(mongo_settings.mongodb_connect_url, my_pipe.name)

debug = True


