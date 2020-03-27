import json
from sklearn.datasets import load_breast_cancer

from photonai.base.json_transformer import JsonTransformer

metadata = """
{
    "name": "basic_svm_pipe",
    "verbosity": 1,
    "permutation_id": null,
    "cache_folder": null,
    "nr_of_processes": 1,
    "random_seed": false,
    "inner_cv": {
        "n_splits": 5,
        "shuffle": false,
        "__photon_type": "KFold"
    },
    "outer_cv": {
        "n_splits": 3,
        "shuffle": false,
        "__photon_type": "KFold"
    },
    "calculate_metrics_across_folds": false,
    "eval_final_performance": true,
    "test_size": 0.2,
    "calculate_metrics_per_fold": true,
    "performance_constraints": null,
    "optimizer": "sk_opt",
    "optimizer_params": {
        "n_configurations": 5
    },
    "metrics": [
        "accuracy",
        "precision",
        "recall",
        "balanced_accuracy"
    ],
    "best_config_metric": "accuracy",
    "output_settings": {
        "mongodb_connect_url": null,
        "save_output": true,
        "plots": true,
        "overwrite_results": false,
        "project_folder": ".",
        "user_id": "",
        "wizard_object_id": "",
        "wizard_project_name": "",
        "__photon_type": "OutputSettings"
    },
    "elements": [
        {
            "initial_name": "StandardScaler",
            "test_disabled": false,
            "__photon_type": "PipelineElement"
        },
        {
            "initial_hyperparameters": {
                "kernel": {
                    "values": [
                        "rbf",
                        "linear"
                    ],
                    "__photon_type": "Categorical"
                },
                "C": {
                    "range_type": "range",
                    "start": 1,
                    "stop": 6,
                    "__photon_type": "FloatRange"
                }
            },
            "initial_name": "SVC",
            "kwargs": {
                "gamma": "scale"
            },
            "test_disabled": false,
            "__photon_type": "PipelineElement"
        }
    ]
}
"""
json_transformer = JsonTransformer()

# Pipe from json-String
metadata_json =json.loads(metadata)
my_pipe = json_transformer.from_json(metadata_json)

# Pipe from json-File
# my_pipe = json_transformer.read_json_file(filepath="./basic_svm_pipe_results_2020-03-27_09-13-56/hyperpipe_config.json")

# WE USE THE BREAST CANCER SET FROM SKLEARN
X, y = load_breast_cancer(True)

my_pipe.fit(X, y)



