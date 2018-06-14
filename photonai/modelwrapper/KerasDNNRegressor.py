import numpy as np
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
from keras.layers import Dropout, Dense
from keras.layers.advanced_activations import PReLU
from keras.layers.core import Activation
from keras.layers.normalization import BatchNormalization
from keras.models import Sequential
from keras.optimizers import Adam
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import ShuffleSplit
from photonai.photonlogger.Logger import Logger
from photonai.modelwrapper.KerasBaseEstimator import KerasBaseEstimator


class KerasDNNRegressor(BaseEstimator, RegressorMixin, KerasBaseEstimator):

    def __init__(self, hidden_layer_sizes=[10, 20], dropout_rate=0.5, act_func='prelu',
                 learning_rate=0.1, batch_normalization=True, nb_epoch=10000, early_stopping_flag=True,
                 eaSt_patience=20, reLe_factor = 0.4, reLe_patience=5, batch_size=64, verbosity=0):
        super(KerasBaseEstimator, self).__init__()
        self.hidden_layer_sizes = hidden_layer_sizes
        self.dropout_rate = dropout_rate
        self.act_func = act_func
        self.learning_rate = learning_rate
        self.target_dimension = 1
        self.batch_normalization = batch_normalization
        self.nb_epoch = nb_epoch
        self.early_stopping_flag = early_stopping_flag
        self.eaSt_patience = eaSt_patience
        self.reLe_factor = reLe_factor
        self.reLe_patience = reLe_patience
        self.verbosity = verbosity
        self.batch_size = batch_size

        self.model = None


    def fit(self, X, y):

        # 1. make model
        self.model = self.create_model(X.shape[1])

        # 2. fit model
        # use callbacks only when size of training set is above 100
        if X.shape[0] > 100:
            # get pseudo validation set for keras callbacks
            splitter = ShuffleSplit(n_splits=1, test_size=0.2)
            for train_index, val_index in splitter.split(X):
                X_train = X[train_index]
                X_val = X[val_index]
                y_train = y[train_index]
                y_val = y[val_index]

            # register callbacks
            callbacks_list = []
            # use early stopping (to save time;
            # does not improve performance as checkpoint will find the best model anyway)
            if self.early_stopping_flag:
                early_stopping = EarlyStopping(monitor='val_loss', patience=self.eaSt_patience)
                callbacks_list += [early_stopping]

            # adjust learning rate when not improving for patience epochs
            reduce_lr = ReduceLROnPlateau(monitor='val_loss',
                                          factor=self.reLe_factor,
                                          patience=self.reLe_patience,
                                          min_lr=0.001,
                                          verbose=self.verbosity)
            callbacks_list += [reduce_lr]

            # fit the model
            results = self.model.fit(X_train, y_train, validation_data=(X_val, y_val),
                                     batch_size=self.batch_size, epochs=self.nb_epoch,
                                     verbose=self.verbosity,  callbacks=callbacks_list)
        else:
            # fit the model
            Logger().debug('Cannot use Keras Callbacks because of small sample size...')
            results = self.model.fit(X, y, batch_size=self.batch_size,
                                     epochs=self.nb_epoch,
                                     verbose=self.verbosity)
        return self

    def predict(self, X):
        return np.squeeze(self.model.predict(X, batch_size=self.batch_size))

    def create_model(self, input_size):

        model = Sequential()
        input_dim = input_size
        for i, dim in enumerate(self.hidden_layer_sizes):
            if i == 0:
                model.add(Dense(dim, input_shape=(input_dim,),  kernel_initializer='random_uniform'))
            else:
                model.add(Dense(dim, kernel_initializer='random_uniform'))

            if self.batch_normalization == 1:
                model.add(BatchNormalization())

            if self.act_func == 'prelu':
                model.add(PReLU(alpha_initializer='zero', weights=None))
            else:
                model.add(Activation(self.act_func))

            model.add(Dropout(self.dropout_rate))

        model.add(Dense(self.target_dimension, activation='linear'))

        # Compile model
        optimizer = Adam(lr=self.learning_rate)
        model.compile(loss='mean_absolute_error', optimizer=optimizer, metrics=['mean_absolute_error'])
        # model.compile(loss='mean_squared_error', optimizer=optimizer, metrics=['mean_squared_error'])

        return model
