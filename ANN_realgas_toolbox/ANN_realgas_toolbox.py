import numpy as np
import pandas as pd
from datetime import datetime
from sklearn import preprocessing, model_selection, metrics

import CoolProp.CoolProp as CP
import os
from shutil import copyfile

import matplotlib.pyplot as plt
#%matplotlib inline

from keras.models import Model, Sequential
from keras.layers import Dense, Activation, Input, BatchNormalization, Dropout
from keras import layers
from keras.callbacks import ModelCheckpoint, EarlyStopping

import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor


'''
Environment to work with different ANN architectures and CoolProp 
'''

class ANN_realgas_toolbox(object):
    def __init__(self):
        self.history = None
        self.predictions = None
       # self.T_test = None
       # self.rho_TP_train = None
       # self.rhoTP_r = None
        self.MinMax_X= []
        self.MinMax_y = []
       # self.T_scaler = None
       # self.T_P_train = None
       # self.rho_vec= None
       # self.p_vec = None
        self.model = None
        self.predictions = None
        self.callbacks_list = None
        #self.fluid= None
        #self.P_max = None
        #self.P_min = None
        #self.nP = None
        #self.T_max = None
        #self.T_min = None
        #self.nT = None
        #
        # self.T_vec = None
        #self.p_c = None
        #self.T_P_test = None
        self.predict_y = None
        #self.rho_test = None
        self.test_points = None
        self.data_dict = None
        self.all_data = None
        self.X_train=None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.y = None
        self.X = None
        self.multiReg=None
        self.targets = None
        self.features = None
        self.best_set = []
        self.best_model = None
        self.predict_for_plot = None
        self.y_for_plot = None


    def res_block(self,input_tensor, n_neuron, stage, block, bn=False):
        ''' creates a resnet (Deep Residual Learning) '''
        conv_name_base = 'res' + str(stage) + block + '_branch'
        bn_name_base = 'bn' + str(stage) + block + '_branch'

        x = Dense(n_neuron, name=conv_name_base + '2a')(input_tensor)
        if bn:
            x = BatchNormalization(axis=-1, name=bn_name_base + '2a')(x)
        x = Activation('relu')(x)

        x = Dense(n_neuron, name=conv_name_base + '2b')(x)
        if bn:
            x = BatchNormalization(axis=-1, name=bn_name_base + '2b')(x)
        x = layers.add([x, input_tensor])
        x = Activation('relu')(x)

        return x

    def import_data(self,path='data_trax/'):
        print('Importing the data...')
        # data files
        files = os.listdir(path)
        # check if csv! and sort
        files = [f for f in files if f[-3:]=='csv']
        files.sort()

        self.data_dict = {}
        for file in files:
            pressure = file[0:2]
            df = pd.read_csv(path+file)
            df['p'] = float(pressure)
            self.data_dict['data_p' + pressure] = df

        del df

        print('Your data dictionary has the following keys: ', self.data_dict.keys())
        print('Now reshaping to one data frame')
        keys = list(self.data_dict.keys())
        keys.sort()
        self.all_data = self.data_dict[keys[0]]
        for num in range(1,len(keys)):
            print(keys[num])
            df = self.data_dict[keys[num]]
            #print(df)
            self.all_data=self.all_data.append(df, ignore_index = True)
            del df

        print('You have ' + str(len(self.all_data)) + ' data points')
        use_cols = list(self.all_data.columns)
        self.all_data = self.all_data[use_cols[1:]]


    def scale_split_data(self, features = ['p','he'], targets = ['rho','T','thermo:psi','thermo:mu','thermo:alpha','thermo:as','thermo:Z','Cp']):
        self.targets = targets
        self.features = features
        self.X = self.all_data[features]
        #self.X = np.array(X)
        self.y = self.all_data[targets]
        #self.y = np.array(y)

        self.MinMax_X = preprocessing.MinMaxScaler()
        self.MinMax_y = preprocessing.MinMaxScaler()

        self.X = self.MinMax_X.fit_transform(self.X)
        self.y = self.MinMax_y.fit_transform(self.y)

        self.X_train, self.X_test, self.y_train, self.y_test = model_selection.train_test_split(self.X, self.y, test_size=0.3, random_state=42)


    # def genTrainData(self, nT=100, T_min=100, T_max=160, nP=100, P_min=100, P_max=2, fluid='nitrogen'):
    #     '''
    #     Generates the test data from coolprop.
    #     input: nT, T_min, T_max, np, P_min, P_max and the fluid
    #     '''
    #     ######################
    #     self.fluid= fluid
    #     self.P_max = P_max
    #     self.P_min = P_min
    #     self.nP = nP
    #     self.T_max = T_max
    #     self.T_min = T_min
    #     self.nT = nT
    #
    #     print('Generate data ...')
    #     # n_train = 20000
    #
    #     n_train = nT * nP
    #
    #     # get critical pressure
    #     self.p_c = CP.PropsSI(fluid, 'pcrit')
    #
    #     self.p_vec = np.linspace(1, 3, nP) * self.p_c
    #     self.T_vec = np.linspace(T_min, T_max, nT)
    #     self.rho_vec = np.asarray([CP.PropsSI('D', 'T', x, 'P', 1.1 * self.p_c, fluid) for x in self.T_vec])
    #
    #     # prepare input
    #     # rho = f(T, P)
    #     # 1. uniform random
    #     self.T_P_train = np.random.rand(n_train, 2)
    #     # 2. family curves
    #     # T_P_train = np.random.rand(n_train, 1)
    #     # tmp = np.ones((nT, nP))* np.linspace(0, 1, nP)
    #     # T_P_train = np.append(T_P_train, tmp.reshape(-1, 1), axis=1)
    #
    #     self.rho_TP_train = np.asarray(
    #         [self.rho_TP_gen(x, fluid) for x in (self.T_P_train * [(self.T_max - self.T_min), (self.P_max - self.P_min) * self.p_c] + [self.T_min, self.p_c])])
    #
    #     # normalize train data
    #     self.rhoTP_scaler = preprocessing.MinMaxScaler()
    #     self.rho_TP_train = self.rhoTP_scaler.fit_transform(self.rho_TP_train.reshape(-1, 1))
    #
    #     # normalize test data
    #     self.T_scaler = preprocessing.MinMaxScaler()
    #     self.T_test = self.T_scaler.fit_transform(self.T_vec.reshape(-1, 1))

    ######################################
    # different ANN model types
    def setResnet(self, indim=2, n_neurons=200, blocks = 2, loss='mse', optimizer='adam', batch_norm=False):
        '''default settings: resnet'''
        ######################
        outdim = len(self.targets)
        print('set up Resnet ANN')
        self.model = None
        alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g']

        # This returns a tensor
        inputs = Input(shape=(indim,))

        # a layer instance is callable on a tensor, and returns a tensor
        x = Dense(n_neurons, activation='relu')(inputs)
        # less then 2 res_block, there will be variance
        for b in range(blocks):
            x = self.res_block(x, n_neurons, stage=1, block=alphabet[b], bn=batch_norm)
            #x = self.res_block(x, n_neurons, stage=1, block='b', bn=batch_norm)
        # last outout layer with linear activation function
        self.predictions = Dense(outdim, activation='linear')(x)

        self.model = Model(inputs=inputs, outputs=self.predictions)
        self.model.compile(loss=loss, optimizer=optimizer, metrics=['accuracy'])

        # checkpoint (save the best model based validate loss)
        try:
            filepath = "./weights.best.hdf5"
        except:
            print('check your fielpath')

        checkpoint = ModelCheckpoint(filepath,
                                     monitor='val_loss',
                                     verbose=1,
                                     save_best_only=True,
                                     mode='min',
                                     period=10)
        early_stop = EarlyStopping(monitor='val_loss', min_delta=0, patience=100, verbose=1, mode='min')
        self.callbacks_list = [checkpoint,early_stop]


    def setSequential(self, indim=2, hiddenLayer=4,n_neurons=200, loss='mse', optimizer='adam', batch_norm=False):
        ######################
        outdim = len(self.targets)
        print('set up Sequential (MLP) ANN')
        self.model = None

        self.model = Sequential()
        self.model.add(Dense(n_neurons, input_dim= indim, activation='relu'))

        # create the hidden layers
        for l in range(hiddenLayer):
            self.model.add(Dense(n_neurons, init='uniform', activation='relu'))
        self.model.add(Dropout(0.2))
        self.model.add(Dense(units=outdim, activation='linear'))

        # model.compile(loss='mean_squared_error', optimizer='sgd', metrics=['accuracy'])
        self.model.compile(loss=loss, optimizer=optimizer, metrics=['accuracy'])

        # checkpoint (save the best model based validate loss)
        try:
            filepath = "./weights.best.hdf5"
        except:
            print('check your fielpath')

        checkpoint = ModelCheckpoint(filepath,
                                     monitor='val_loss',
                                     verbose=1,
                                     save_best_only=True,
                                     mode='min',
                                     period=10)
        early_stop = EarlyStopping(monitor='val_loss', min_delta=0, patience=100, verbose=1, mode='min')
        self.callbacks_list = [checkpoint, early_stop]


    def fitModel(self, batch_size=1024, epochs=400, vsplit=0.1):
        # fit the model
        a = datetime.now()
        self.history = self.model.fit(
            # T_train, rho_train,
            self.X_train, self.y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=vsplit,
            verbose=2,
            callbacks=self.callbacks_list,
            shuffle=True)
        b = datetime.now()
        c = b-a
        print('The training took: ' + str(int(c.total_seconds()))+' seconds.')


    def prediction(self):
        # loads the best weights
        self.model.load_weights("./weights.best.hdf5")

        self.predict_y = self.model.predict(self.X_test)


    def plotLoss(self):
        #######################
        # plot loss
        #######################
        fig = plt.figure(1)
        plt.semilogy(self.history.history['loss'])
        #if vsplit:
        plt.semilogy(self.history.history['val_loss'])
        plt.title('mse')
        plt.ylabel('loss')
        plt.xlabel('epoch')
        plt.legend(['train', 'test'], loc='upper right')
        plt.show(block=False)


    # def plotPredict(self):
    #     #######################
    #     # 1.Plot actual vs prediction for training set
    #     #######################
    #     fig = plt.figure(2)
    #     for prdt, ref in zip(self.rho_predict, self.rho_test):
    #         plt.plot(self.T_scaler.inverse_transform(self.T_test), self.rhoTP_scaler.inverse_transform(prdt), 'b-')
    #         plt.plot(self.T_scaler.inverse_transform(self.T_test), self.rhoTP_scaler.inverse_transform(ref), 'r:')
    #     plt.legend(['predict', 'CoolProp'], loc='upper right')
    #     plt.title(self.test_points)
    #     plt.show(block=False)

    def plotAccuracy(self, target = 'rho', all = False):
        #######################
        # 2.L2 accuracy plot
        # Compute R-Square value for test set
        #######################
        column_list = list(self.targets)

        if all:
            for i, tar in enumerate(column_list):
                TestR2Value = metrics.r2_score(self.predict_y[:, i], self.y_test[:, i])
                print("Training Set R-Square=", TestR2Value)

                fig = plt.figure(100+i)
                plt.plot(self.predict_y[:, i], self.y_test[:, i], 'k^', ms=3, mfc='none')
                plt.title('R2 =' + str(TestR2Value) + 'for: '+tar)

        else:

            target_id = [ind for ind, x in enumerate(column_list) if x == target]
            target_id = target_id[0]

            TestR2Value = metrics.r2_score(self.predict_y[:, target_id], self.y_test[:, target_id])
            print("Test Set R-Square=", TestR2Value)

            fig = plt.figure(3)
            plt.plot(self.predict_y[:, target_id], self.y_test[:, target_id], 'k^', ms=3, mfc='none')
            plt.title('R2 =' + str(TestR2Value))

        plt.show(block=False)


    def plotPredict(self, pressure = 20., target = 'T'):
        # resacle your data
        y_test_rescaled = self.MinMax_y.inverse_transform(self.y_test)
        X_test_rescaled = self.MinMax_X.inverse_transform(self.X_test)
        predict_rescaled = self.MinMax_y.inverse_transform(self.predict_y)

        # sort your X data according to ascending pressure
        sort_id = np.argsort(X_test_rescaled[:,0])
        y_sorted = y_test_rescaled[sort_id[::]]
        X_sorted = X_test_rescaled[sort_id[::]]
        predict_sorted = predict_rescaled[sort_id[::]]
        print(predict_sorted)

        vals = pressure
        ix = np.isin(X_sorted[:,0], vals)
        index = np.where(ix)
        index=index[:][0]
        print(index)

        column_list = list(self.targets)

        # find the index of the target label
        target_id=[ind for ind, x in enumerate(column_list) if x==target]
        target_id = target_id[0]
        print(target_id)

        self.y_for_plot = y_sorted[index,target_id]
        self.predict_for_plot = predict_sorted[index, target_id]
        print(self.predict_for_plot)

        self.y_for_plot.sort()
        self.predict_for_plot.sort()

        plt.figure(10)
        plt.title('Compare prediction and y_test for field: '+target)
        plt.plot(self.y_for_plot, '*')
        plt.plot(self.predict_for_plot, '*')
        plt.legend(['y_test','predict'])
        plt.show(block=False)

    # performs parametric search for the Sequential model
    def gridSearchSequential(self, neurons = [50,100,200,400], layers = [2,3,4,5,6], epochs = [100,200,500], batch= [100,200,500,1000],loss_func = ['mse']):

        best_score = 999999
        for n in neurons:
            for l in layers:
                for lossf in loss_func:
                    self.setSequential(indim=2, hiddenLayer=l, loss=lossf)
                    for e in epochs:
                        for b in batch:
                            try:
                                self.model.load_weights("./weights.best.hdf5")
                            except:
                                print('No weights yet')
                            # fit the model and apply it to the test set
                            self.fitModel(batch_size=b, epochs=e)
                            self.prediction()
                            R2 = abs(metrics.r2_score(self.predict_y,self.y_test))
                            mse = abs(metrics.mean_squared_error(self.predict_y,self.y_test))
                            print('')
                            print('R2 is: ', R2)
                            print('MSE is: ', mse)
                            #save the best set according to R2 value
                            if mse < best_score:
                                # store the best combination of parameters
                                self.best_set = [n, l, e,b,lossf]
                                best_score= mse#R2
                                self.best_model = self.model
                                # store the best weights separately
                                copyfile("./weights.best.hdf5","./weights.best_R2.hdf5")
        print(' ')
        print('best metrics score: ', best_score)

    # performs parametric search for the Sequential model
    def gridSearchResNet(self, neurons = [200,400,600], layers = [3,4,5], epochs = [500,600,800], batch= [1000,2000], loss_func = ['mse']):

        best_score = 999999
        for n in neurons:
            for l in layers:
                for lossf in loss_func:
                    self.setResnet(indim=2, n_neurons=n, blocks=l, batch_norm=True)
                    for e in epochs:
                        for b in batch:
                            try:
                                self.model.load_weights("./weights.best.hdf5")
                            except:
                                print('No weights yet')
                            # fit the model and apply it to the test set
                            self.fitModel(batch_size=b, epochs=e)
                            self.prediction()
                            R2 = abs(metrics.r2_score(self.predict_y,self.y_test))
                            mse = abs(metrics.mean_squared_error(self.predict_y,self.y_test))
                            print('')
                            print('R2 is: ', R2)
                            print('MSE is: ', mse)
                            #save the best set according to R2 value
                            if mse < best_score:
                                # store the best combination of parameters
                                self.best_set = [n, l, e,b,lossf]
                                best_score= mse#R2
                                self.best_model = self.model
                                # store the best weights separately
                                copyfile("./weights.best.hdf5","./weights.best_R2.hdf5")
        print(' ')
        print('best metrics score: ', best_score)



    # XGBoost classifier!
    def xgboost(self,depth = 7):
        tuned_params = {"objective":"reg:linear",'colsample_bytree': 0.3, 'learning_rate': 0.1, 'max_depth': depth}
        self.multiReg = MultiOutputRegressor(xgb.XGBRegressor(objective='reg:linear', params = tuned_params))
        self.multiReg.fit(self.X_train,self.y_train)
        self.predict_y = self.multiReg.predict(self.X_test)
        score = metrics.r2_score(self.predict_y, self.y_test)
        print('The R2 score from XGBoost is: ',score)











