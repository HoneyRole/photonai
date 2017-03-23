import pandas as pd
import nibabel as nib
import os
import numpy as np
import scipy.io as spio


#Todo: make sure that each class is returning an pandas DataFrame Object

class MatLoader(object):

    def __call__(self, filename, **kwargs):
        mat_data = self.load_mat(filename)
        if 'var_name' in kwargs:
            var_name = kwargs.get('var_name')
            mat_data = mat_data[var_name]
        return pd.DataFrame(data=mat_data)

    def load_mat(self, filename):
        '''
        this function should be called instead of direct spio.loadmat
        as it cures the problem of not properly recovering python dictionaries
        from mat files. It calls the function check keys to cure all entries
        which are still mat-objects
        '''
        data = spio.loadmat(filename, struct_as_record=False,
                            squeeze_me=True)
        return self._check_keys(data)

    def _check_keys(self, item_dict):
        '''
        checks if entries in dictionary are mat-objects. If yes
        todict is called to change them to nested dictionaries
        '''
        for key in item_dict:
            if isinstance(item_dict[key],
                          spio.matlab.mio5_params.mat_struct):
                item_dict[key] = self._to_dict(item_dict[key])
        return item_dict

    def _to_dict(self, matobj):
        '''
        A recursive function which constructs from matobjects nested dictionaries
        '''
        return_dict = {}
        for strg in matobj._fieldnames:
            elem = matobj.__dict__[strg]
            if isinstance(elem, spio.matlab.mio5_params.mat_struct):
                return_dict[strg] = self._to_dict(elem)
            else:
                return_dict[strg] = elem
        return return_dict


class CsvLoader(object):

    def __call__(self, filename, **kwargs):
        csv_data = pd.read_csv(filename, **kwargs)
        return csv_data


class XlsxLoader(object):

    def __call__(self, filename, **kwargs):
        return pd.read_excel(filename)


class NiiLoader(object):
    # Todo: Currently only works when reshaping 3d nii to a 1d vector

    def __call__(self, directory, **kwargs):
        # get nifti filenames in specified directory
        # get rid of asterisk in directory
        # os.path.split will take head and tail of path
        # only use the head
        directory, _ = os.path.split(directory)
        filenames = self.get_filenames(directory)

        # iterate over and load every .nii file
        # this requires one nifti per subject
        data = []
        for ind_sub in range(len(filenames)):
            filename = os.path.join(directory, filenames[ind_sub])
            img = nib.load(filename)
            data.append(img.get_data())

        # stack list elements to matrix
        data = np.stack(data, axis=0)
        data = np.reshape(data, (data.shape[0], data.shape[1] *
                                 data.shape[2] * data.shape[3]))
        # save as numpy array and load with memory map
        np.save((directory + '/photon_data.npy'), data)
        del data
        data = np.load((directory + '/photon_data.npy'), mmap_mode='r')
        return pd.DataFrame(data)


    def get_filenames(self, directory):
        filenames = []
        for file in os.listdir(directory):
            if file.endswith(".nii"):
                filenames.append(file)
        # check if files have been found
        if len(filenames) == 0:
            raise ValueError('There are no .nii-files in the '
                             'specified folder!')
        else:
            return filenames