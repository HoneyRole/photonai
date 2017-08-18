# register Elements, Optimizers, ...?
import json
import os.path

class RegisterPipelineElement:
    def __init__(self, photon_package, photon_name, class_str=None, element_type=None):
        self.photon_name = photon_name
        self.photon_package = photon_package
        self.class_str = class_str
        self.element_type = element_type

    def add(self):
        # register_element and jsonify
        content = PhotonRegister.get_json(self.photon_package)  # load existing json
        duplicate = self.check_duplicate(content)
        if not duplicate:
            print('Adding PipelineElement ' + self.class_str + ' to ' + self.photon_package + ' as "' + self.photon_name + '".')

            # add new element
            content[self.photon_name] = self.class_str, self.element_type

            # write back to file
            PhotonRegister.write2json(content, self.photon_package)
            # print(register_element.__dict__)

    def remove(self):
        content = PhotonRegister.get_json(self.photon_package)  # load existing json
        print('Removing the PipelineElement named "' + self.photon_name
              + '" (' + content[self.photon_name][0] + '.' + content[self.photon_name][
                  1] + ')' + ' from ' + self.photon_package + '.')

        if self.photon_name in content: del content[self.photon_name]
        PhotonRegister.write2json(content, self.photon_package)

    def check_duplicate(self, content):
        # check for duplicate name (dict key)
        flag = 0
        if self.photon_name in content:
            flag += 1
            print('The PipelineElement named "' + self.photon_name + '" has already been registered in '
                  + self.photon_package + ' with ' + content[self.photon_name][0] + '.')

        # check for duplicate class_str
        if any(self.class_str in s for s in content.values()):
            flag += 1
            for key_str, values_str in content.items():
                if self.class_str in values_str:
                    which = key_str
            print('The PipelineElement with the ClassName "' + self.class_str + '" has already been registered in '
                  + self.photon_package + ' as "' + which + '". "' + self.photon_name + '" not added to ' + self.photon_package + '.')

        return flag > 0

    def get_pipeline_element_infos(photon_package):
        class_info = dict()
        for package in photon_package:
            content = PhotonRegister.get_json(package)
            n = 2
            for key in content:
                class_path, class_name = os.path.splitext(content[key][0])
                class_info[key] = class_path, class_name[1:]

        return class_info

class PhotonRegister:
    def __init__(self):
        pass

    # one json file per Photon Package (Core, Neuro, Genetics, Designer (if necessary)
    @staticmethod
    def get_json(photon_package):
        file_name = photon_package + '.json'
        import os.path
        if os.path.isfile(file_name):
            # Reading json
            with open(file_name, 'r') as f:
                file_content = json.load(f)
        else:
            file_content = dict()
            print(file_name + ' not found. Creating file.')

        #flat_list = [file_content for sublist in file_content for item in sublist]

        return file_content

    @staticmethod
    def write2json(content2write, photon_package):
        file_name = photon_package + '.json'

        # Writing JSON data
        with open(file_name, 'w') as f:
           json.dump(content2write, f)

            # print('Writing to ' + file_name)


# if __name__ == '__main__':
#
    # import sklearn
    # import inspect
    # for name, obj in inspect.getmembers(sklearn):
    #     #print(obj)
    #     print(name)
    #
    # #print(hasattr(PCA(), '_estimator_type'))

    # ELEMENT_DICTIONARY = RegisterPipelineElement.get_pipeline_element_infos(['PhotonCore', 'PhotonCore2'])
    # print(ELEMENT_DICTIONARY)

    # photon_package = 'PhotonCore2'  # where to add the element
    # photon_name = 'skjhvr'  # element name
    # class_str = 'sklearn.svm.SljkVR'  # element info
    # element_type = 'Estimator'  # element type
    # RegisterPipelineElement(photon_name=photon_name,
    #                         photon_package=photon_package,
    #                         class_str=class_str,
    #                         element_type=element_type).add()
    #
    # photon_name = 'slkjvr' # elment name
    # class_str = 'sklearn.test'  # element info
    # RegisterPipelineElement(photon_name=photon_name,
    #                         photon_package=photon_package,
    #                         class_str=class_str,
    #                         element_type=element_type).add()

    # photon_name = 'Test'  # element name
    # class_str = 'sklearn.svm.SVR'  # element info
    # RegisterPipelineElement(photon_name=photon_name,
    #                         photon_package=photon_package,
    #                         class_str=class_str,
    #                         element_type=element_type).add()
    #
    # photon_name = 'PCA'  # element name
    # class_str = 'sklearn.decomposition.PCA' # element info
    # element_type = 'Transformer' # element type
    # RegisterPipelineElement(photon_name=photon_name,
    #                         photon_package=photon_package,
    #                         class_str=class_str,
    #                         element_type=element_type).add()
    #
    # eldict = RegisterPipelineElement.get_pipeline_element_infos('PhotonCore')
    # # eldict = PhotonRegister.get_element_infos('PhotonCore')
    # print(eldict['svr'][0])
    # print(eldict['svr'][1])
    #
    # RegisterPipelineElement(photon_name='PCA',
    #                         photon_package=photon_package).remove()


    # # Write complete dict to json (OVERWRITES EVERYTHING IN IT!!!)
    #
    # ELEMENT_DICTIONARY = {'pca': ('sklearn.decomposition', 'PCA'),
    #                       'svc': ('sklearn.svm', 'SVC'),
    #                       'knn': ('sklearn.neighbors', 'KNeighborsClassifier'),
    #                       'logistic': ('sklearn.linear_model', 'LogisticRegression'),
    #                       'dnn': ('PipelineWrapper.TFDNNClassifier', 'TFDNNClassifier'),
    #                       'KerasDNNClassifier': ('PipelineWrapper.KerasDNNClassifier',
    #                                              'KerasDNNClassifier'),
    #                       'standard_scaler': ('sklearn.preprocessing', 'StandardScaler'),
    #                       'wrapper_model': ('PipelineWrapper.WrapperModel', 'WrapperModel'),
    #                       'test_wrapper': ('PipelineWrapper.TestWrapper', 'WrapperTestElement'),
    #                       'ae_pca': ('PipelineWrapper.PCA_AE_Wrapper', 'PCA_AE_Wrapper'),
    #                       'rl_cnn': ('photon_core.PipelineWrapper.RLCNN', 'RLCNN'),
    #                       'CNN1d': ('PipelineWrapper.CNN1d', 'CNN1d'),
    #                       'SourceSplitter': ('PipelineWrapper.SourceSplitter', 'SourceSplitter'),
    #                       'f_regression_select_percentile':
    #                           ('PipelineWrapper.FeatureSelection', 'FRegressionSelectPercentile'),
    #                       'f_classif_select_percentile':
    #                           ('PipelineWrapper.FeatureSelection', 'FClassifSelectPercentile'),
    #                       'py_esn_r': ('PipelineWrapper.PyESNWrapper', 'PyESNRegressor'),
    #                       'py_esn_c': ('PipelineWrapper.PyESNWrapper', 'PyESNClassifier'),
    #                       'SVR': ('sklearn.svm', 'SVR'),
    #                       'KNeighborsRegressor': ('sklearn.neighbors', 'KNeighborsRegressor'),
    #                       'DecisionTreeRegressor': ('sklearn.tree','DecisionTreeRegressor'),
    #                       'RandomForestRegressor': ('sklearn.ensemble', 'RandomForestRegressor'),
    #                       'KerasDNNRegressor': ('PipelineWrapper.KerasDNNRegressor','KerasDNNRegressor'),
    #                       'PretrainedCNNClassifier': ('PipelineWrapper.PretrainedCNNClassifier', 'PretrainedCNNClassifier')
    #                       }
    # PhotonRegister.write2json(ELEMENT_DICTIONARY, 'PhotonCore')
