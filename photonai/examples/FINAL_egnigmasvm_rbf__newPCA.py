        
# -------------------- GENERATED WITH PHOTON WIZARD (beta) ------------------------------
# PHOTON Code File (Photon Syntax): 
# /spm-data/Scratch/photon_wizard/nopel/enigmasvmnewpca/photon_code.py

import pandas as pd
import numpy as np
from sklearn.model_selection import *

from photonai.base.PhotonBase import Hyperpipe, PipelineElement, OutputSettings
from photonai.optimization.Hyperparameters import Categorical, IntegerRange, FloatRange

# Load data
df = pd.read_excel('/spm-data/Scratch/photon_wizard/nopel/FINAL_svm5fold/BMIGr.xlsx')
X = np.asarray(df.iloc[:,1::])
y = np.asarray(df.iloc[:,0])
            
group_var = None
                
# Define cross-validation strategies
outer_cv = KFold(n_splits=5,shuffle=True)
inner_cv = KFold(n_splits=5, shuffle=True)

# Specify how results are going to be saved
output_settings = OutputSettings(mongodb_connect_url="mongodb://trap-umbriel:27017/photon_results",
                                 save_predictions="best",
                                 save_feature_importances="None",
                                 project_folder="/spm-data/Scratch/photon_wizard/nopel/FINAL_svm5fold",
                                 user_id="nopel",
                                 wizard_object_id="5c5c37f8fb753a9f3e5af976",
                                 wizard_project_name="enigmasvmnewpca")
                
# Define hyperpipe
hyperpipe = Hyperpipe('enigmasvmnewpca',
                        optimizer='sk_opt', optimizer_params={},
                        metrics=['accuracy', 'precision', 'recall', 'balanced_accuracy', 'sensitivity', 'specificity', 'f1_score', 'auc'],
                        best_config_metric='f1_score',
                        outer_cv=outer_cv,
                        inner_cv=inner_cv,
                        eval_final_performance=True,
                        verbosity=0,
                        output_settings=output_settings,
                        groups=group_var)
                
# Add transformer elements
hyperpipe += PipelineElement("SimpleImputer", hyperparameters={}, 
                             test_disabled=False, missing_values=np.nan, strategy='mean', fill_value=0)
hyperpipe += PipelineElement("StandardScaler", hyperparameters={}, 
                             test_disabled=False, with_mean=True, with_std=True)
hyperpipe += PipelineElement("PCA", hyperparameters={'n_components': IntegerRange(5,150)},
                             test_disabled=False)
hyperpipe += PipelineElement("ImbalancedDataTransform", hyperparameters={}, 
                             test_disabled=False, method_name='RandomUnderSampler')
# Add estimator
hyperpipe += PipelineElement("SVC", hyperparameters={'C': FloatRange(0.5, 2)}, gamma='scale', kernel='rbf')
             

import time
start_time = time.time()
# NOW TRAIN YOUR PIPELINE
# Fit hyperpipe
hyperpipe.fit(X, y)
# your code
elapsed_time = time.time() - start_time
print(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
                

# call PHOTON Investigator for a visualization of results 
# from photonai.investigator.Investigator import Investigator
# Investigator.show(hyperpipe)
        
        
