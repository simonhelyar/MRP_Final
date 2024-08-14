#Simon Helyar#Major Research Project#Importing relevant librariesimport pandas as pdimport numpy as npfrom geopy import distanceimport seaborn as snsimport matplotlib.pyplot as pltfrom statsmodels.tsa.stattools import adfuller, kpssfrom sklearn.preprocessing import MinMaxScalerfrom sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_scoreimport xgboostfrom sklearn.ensemble import RandomForestRegressorfrom tensorflow.keras.models import Sequentialfrom tensorflow.keras.layers import Dense, LSTM, Bidirectional, Input, Dropoutfrom sklearn.multioutput import MultiOutputRegressorfrom stellargraph.layer import FixedAdjacencyGraphConvolutionimport networkx as nxfrom sklearn.model_selection import GridSearchCVfrom keras_tuner.tuners import RandomSearchfrom tensorflow.keras.optimizers.legacy import Adamfrom sklearn.linear_model import LinearRegression#Disabling warnings related to M1 Apple Chip and tensorflow 2.12 that don't effect performanceimport logging, osos.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'logging.getLogger("tensorflow").setLevel(logging.ERROR)logging.getLogger("tensorflow").addHandler(logging.NullHandler(logging.ERROR))#Changing run settings and color palettepd.set_option('display.max_columns', None)pd.options.mode.chained_assignment = Nonemy_cmap = sns.color_palette("Blues", as_cmap=True)#Set parameter options look_back = 14look_ahead = 3wildfire_features = Trueif wildfire_features:    feature_count = 10else:    feature_count = 8#Air quality station names and dataset foldersStationsList = ['ThunderBay', 'SaultSteMarie', 'NorthBay', 'ParrySound', 'Ottawa',  'Belleville', 'Barrie', 'Toronto', 'London', 'Windsor']dataset_folder = '/Users/Simon Helyar/Desktop/TMU/MRP/FinalData'dataset_fire = '/Users/Simon Helyar/Desktop/TMU/MRP/FinalData/FireData_post2001.csv'#Processing the data from the datasetsdf_fire_temp = pd.read_csv(dataset_fire, low_memory=False)df_fire = df_fire_temp[df_fire_temp['REP_DATE'].notna()]df_fire.OUT_DATE.fillna(df_fire.REP_DATE)df_fire['OUT_DATE'] = pd.to_datetime(df_fire.OUT_DATE).dt.datedf_fire['REP_DATE'] = pd.to_datetime(df_fire.REP_DATE).dt.datedf = pd.DataFrame()for station in StationsList:    filepath = dataset_folder + '/' + station + '_dataset.csv'    df_station = pd.read_csv(filepath)        df = pd.concat([df,df_station])df = df.reset_index(drop=True)  df['PM2.5_DailyAvg'] = pd.to_numeric(df['PM2.5_DailyAvg'],errors = 'coerce')  print(df.columns)    print(df.dtypes)#Printing number of missing PM2.5 values by stationdf_missing = df[df['PM2.5_DailyAvg'].isnull()]print(df_missing.groupby(['Station'])['Station'].count())#Filling missing values using a rolling meandf['PM2.5_DailyAvg'] = df['PM2.5_DailyAvg'].fillna(df['PM2.5_DailyAvg'].rolling(65,min_periods=1, center = True).mean()) numeric_columns = df.select_dtypes(include=['number']).columnsdf[numeric_columns] = df[numeric_columns].fillna(0) df['Date'] = pd.to_datetime(df.Date).dt.date#Adding the wildfire features to the datasetif wildfire_features:    df["ActiveFire1000km"] = np.nan    df["ActiveFire500km"] = np.nan    df["ClosestFire1000km"] = np.nan    df["FireSize_0.5Hectares"] = np.nan    for index, row in df.iterrows():        date = row['Date']            fire_distances = []        active_fires = 0        firesize = 0        fire500km = 0            df_fire_temp = df_fire[(df_fire['REP_DATE'] >= date) & (df_fire['OUT_DATE'] <= date)]        for index_fire, row_fire in df_fire_temp.iterrows():             fire_cor = (row_fire['LATITUDE'], row_fire['LONGITUDE'])            station_cor = (row['Latitude'], row['Longitude'])            fire_dist = distance.distance(fire_cor, station_cor).km            if fire_dist <= 500:                fire500km = 1                                if fire_dist <= 1000:                active_fires = 1                fire_distances.append(fire_dist)                if row_fire['SIZE_HA'] >= 0.5:                    firesize = 1        if active_fires == 0:            df.loc[index, 'ActiveFire1000km'] = 0            df.loc[index, 'ClosestFire1000km'] = 0            df.loc[index, "FireSize_0.5Hectares"] = 0            df.loc[index, "ActiveFire500km"] = 0            else:            closest_fire = round(np.min(fire_distances),3)                   df.loc[index, 'ActiveFire1000km'] = active_fires            df.loc[index, 'ClosestFire1000km'] = closest_fire            df.loc[index, "FireSize_0.5Hectares"] = firesize            df.loc[index, "ActiveFire500km"] = fire500km    df["ClosestFire1000km"] = pd.to_numeric(df["ClosestFire1000km"],errors = 'coerce')#Feature correlation heatmapfig, ax1 = plt.subplots(figsize=(15,10))  df_heatmap = df.copy()df_heatmap = df_heatmap.drop(columns=['Station ID', 'Latitude', 'Longitude', 'Station', 'Date'])sns.heatmap(df_heatmap.corr(), ax = ax1, annot=True, cmap=my_cmap)plt.show() #Plot of PM2.5 values with rolling meanfig, axs = plt.subplots(nrows=int(len(StationsList)/2), ncols=2, sharey=True, figsize=(15,15))fig.subplots_adjust(hspace = .4, wspace=.001)station_index = 0for i in range(int(len(StationsList)/2)):    for j in range(2):                   df_i = df[df['Station'] == StationsList[station_index]]               df_i.loc[:, '7day_rolling_avg'] = df_i["PM2.5_DailyAvg"].rolling(7).mean()        axs[i,j].plot(df_i["Date"], df_i["PM2.5_DailyAvg"], label = 'Data', color = 'navy')        axs[i,j].plot(df_i['Date'], df_i['7day_rolling_avg'], label = 'RollingAverage', color = 'lightblue')         axs[i,j].set_title(StationsList[station_index])        axs[i,j].legend()        station_index += 1        plt.show() #Boxplot of PM2.5 values by stationsns.boxplot(data=df, x="PM2.5_DailyAvg", y="Station", color = 'cornflowerblue')plt.show() #Plot of wildfire feature correlations by stationfig2, axs2 = plt.subplots(nrows=int(len(StationsList)/2), ncols=2, sharey=True, sharex=True, figsize=(15,15))fig2.subplots_adjust(hspace = .1, wspace=.1)station_index_2 = 0for i in range(int(len(StationsList)/2)):    for j in range(2):                   df_i = df[df['Station'] == StationsList[station_index_2]]         df_i = df_i.filter(items=["PM2.5_DailyAvg",  'ActiveFire1000km', 'ActiveFire500km', 'ClosestFire1000km', "FireIn500km", "FireSize_0.5Hectares"])         sns.heatmap(df_i.corr()[["PM2.5_DailyAvg"]], ax = axs2[i,j], annot=True, cbar = False, cmap=my_cmap, annot_kws={"size": 14})        axs2[i,j].set_title(StationsList[station_index_2])        station_index_2 += 1        plt.show()#Heatmap of station correlationsdf_stationcorr = pd.DataFrame()for i in range(len(StationsList)):     df_i = df[df['Station'] == StationsList[i]]     df_i_pm = pd.DataFrame(data = df_i["PM2.5_DailyAvg"]).reset_index()    df_i_pm = df_i_pm.drop(columns=df_i_pm.columns[0])    df_i_pm = df_i_pm.rename(columns={df_i_pm.columns[0]: StationsList[i]})    df_stationcorr = pd.concat([df_stationcorr,df_i_pm], axis = 1)fig, ax4 = plt.subplots(figsize=(15,10)) sns.heatmap(df_stationcorr.corr(), annot=True, ax = ax4, cmap=my_cmap)plt.show()#ADF and KPSS stationarity testsstationary_results = pd.DataFrame({})for i in range(len(StationsList)):    df_stat = df[df['Station'] == StationsList[i]]         adfuller_list = list(adfuller(df_stat["PM2.5_DailyAvg"], autolag='AIC'))    kpss_list = list(kpss(df_stat["PM2.5_DailyAvg"]))    adf_kpss = pd.DataFrame(data = {'Station': StationsList[i], 'adf_teststatistic': adfuller_list[0], 'adf_5%criticalvalue': adfuller_list[4]['5%'], 'adf_p-value': adfuller_list[1], 'kpss_teststatistic': kpss_list[0], 'kpss_5%criticalvalue': kpss_list[3]['5%'], 'kpss_p-value': kpss_list[1]}, index = [i])    stationary_results = pd.concat([stationary_results, adf_kpss], ignore_index=True)print(stationary_results)#Process the data for machine learning modelsdef create_dataset(X, y, look_back, look_ahead):    dataX, dataY = [], []    for i in range(len(X) - look_back - look_ahead + 1):        a = y[i:(i + look_back)]        dataX.append(np.concatenate((X[i], a)))        dataY.append(y[i + look_back:i + look_back + look_ahead])    return np.array(dataX), np.array(dataY)#Process the data for RNN modelsdef create_dataset_rnn(X, y, look_back, look_ahead):    dataX, dataY = [], []    X = np.concatenate((X, y.reshape(-1,1)), axis=1)    for i in range(len(X) - look_back - look_ahead + 1):        a = X[i:(i + look_back),:]        dataX.append(a)        dataY.append(y[i + look_back:i + look_back + look_ahead])    return np.array(dataX), np.array(dataY)#Create the final dataframe outputdf_output = pd.DataFrame({})df = df.set_index('Date')scaler = MinMaxScaler(feature_range = (0, 1))df_categ = df.filter(items = ['Station ID', 'Station', 'Latitude', 'Longitude'])df_num = df.drop(['Station ID', 'Station', 'Latitude', 'Longitude'], axis=1)df = pd.DataFrame(scaler.fit_transform(df_num), columns=df_num.columns, index=df_num.index)df = pd.concat([df, df_categ], axis = 1)df_spatial = pd.DataFrame(df.groupby(df.Station)['PM2.5_DailyAvg'].apply(lambda x: x.values).values.tolist(), index=df.Station.unique())train_rate = 0.8#Process the data for GCN modeldef train_test_split_spatial(data, train_portion):    time_len = data.shape[1]    train_size = int(time_len * train_portion)    train_data = np.array(data.iloc[:, :train_size])    test_data = np.array(data.iloc[:, train_size:])    return train_data, test_datatrain_data, test_data = train_test_split_spatial(df_spatial, train_rate)def sequence_data_preparation(look_back, look_ahead, train_data, test_data):    trainX, trainY, testX, testY = [], [], [], []    for i in range(train_data.shape[1] - int(look_back + look_ahead - 1)):        a = train_data[:, i : i + look_back + look_ahead]        trainX.append(a[:, :look_back])        trainY.append(a[:, look_back:].reshape(10 * look_ahead))            for i in range(test_data.shape[1] - int(look_back + look_ahead - 1)):        b = test_data[:, i : i + look_back + look_ahead]        testX.append(b[:, :look_back])        testY.append(b[:, look_back:].reshape(10 * look_ahead))    trainX = np.array(trainX)    trainY = np.array(trainY)    testX = np.array(testX)    testY = np.array(testY)    return trainX, trainY, testX, testY#Create GCN train and test setsX_train_GCN, y_train_GCN, X_test_GCN, y_test_GCN = sequence_data_preparation(look_back, look_ahead, train_data, test_data)df_stationcorr = pd.DataFrame()for i in range(len(StationsList)):     df_i = df[df['Station'] == StationsList[i]]     df_i_pm = pd.DataFrame(data = df_i["PM2.5_DailyAvg"]).reset_index()    df_i_pm = df_i_pm.drop(columns=df_i_pm.columns[0])    df_i_pm = df_i_pm.rename(columns={df_i_pm.columns[0]: StationsList[i]})    df_stationcorr = pd.concat([df_stationcorr,df_i_pm], axis = 1)#Create adjency matrix for GCN model input    df_corr = df_stationcorr.corr()df_corr[df_corr >= 0.75] = 1df_corr[df_corr < 0.75] = 0adj_matrix = df_corr#GCN MODELdef gcn_model(hp):    gcn_model = Sequential()    gcn_model.add(Input(shape=(X_train_GCN.shape[1], look_back)))    gcn_model.add(FixedAdjacencyGraphConvolution(hp.Choice('gcn_units1', [16, 32, 64]), A = adj_matrix, activation = 'relu'))    gcn_model.add(FixedAdjacencyGraphConvolution(hp.Choice('gcn_units2', [16, 32, 64]), A = adj_matrix, activation = 'relu'))    gcn_model.add(LSTM(hp.Choice('lstm_units', [32, 64, 86]), activation= "relu", return_sequences=False))    gcn_model.add(Dropout(hp.Choice('dropout', [0.2, 0.3, 0.4])))    gcn_model.add(Dense(10 * look_ahead, activation= "relu"))    learning_rate = hp.Choice('lr', [0.0001, 0.001, 0.01])    gcn_model.compile(loss='mean_squared_error', optimizer = Adam(learning_rate=learning_rate))    return gcn_model#GCN model hyperparameter tuningrsearch_gcn = RandomSearch(gcn_model, objective='val_loss', overwrite = True)#, project_name='stacked_lstm_tuner')rsearch_gcn.search(X_train_GCN, y_train_GCN, epochs=25, validation_split = 0.3, verbose = 0)best_hp_gcn = rsearch_gcn.get_best_hyperparameters()[0]gcn_best_model = rsearch_gcn.get_best_models(num_models=1)gcn_model = gcn_best_model[0]#GCN model predictions    gcn_pred = gcn_model.predict(X_test_GCN)stationlabels = {0:'ThunderBay', 1:'SaultSteMarie', 2:'NorthBay', 3:'ParrySound', 4:'Ottawa',  5:'Belleville', 6:'Barrie', 7:'Toronto', 8:'London', 9:'Windsor'}#Create station network plotdef show_graph_with_labels(adjacency_matrix, mylabels):    rows, cols = np.where(adjacency_matrix == 1)    edges = zip(rows.tolist(), cols.tolist())    gr = nx.Graph()    gr.add_edges_from(edges)    pos = nx.spring_layout(gr, k=1.25)    nx.draw(gr, pos, node_size=500, labels=mylabels, with_labels=True)    plt.show()show_graph_with_labels(adj_matrix, stationlabels)#GCN model evaluation metricsgcn_mae = mean_absolute_error(y_test_GCN, gcn_pred)gcn_rmse = root_mean_squared_error(y_test_GCN, gcn_pred)gcn_r2 = r2_score(y_test_GCN, gcn_pred) final_pred = []#Iterate through each station's data and create modelsfor i in range(len(StationsList)):     #Filter data for relevant station    df_i = df[df['Station'] == StationsList[i]].drop(['Station ID', 'Station', 'Latitude', 'Longitude'], axis=1)        #Prepare data for machine learning models    X_scaled = df_i.drop(columns=['PM2.5_DailyAvg']).to_numpy()    y_scaled = df_i['PM2.5_DailyAvg'].to_numpy()    X_window, y_window = create_dataset(X_scaled, y_scaled, look_back, look_ahead)        #Prepare data for RNN models    X_rnn, y_rnn = create_dataset_rnn(np.array(X_scaled), np.array(y_scaled), look_back, look_ahead)        df_y = pd.DataFrame(y_rnn)    df_y.to_csv("out_y.csv")    df_x = pd.DataFrame(X_rnn.flatten())    df_x.to_csv("out_x.csv")     train_size = int(len(y_scaled) * train_rate)        #Split data into train and test sets    X_train_rnn = X_rnn[:train_size,:]    y_train_rnn = y_rnn[:train_size]    X_test_rnn = X_rnn[train_size:,:]    y_test_rnn = y_rnn[train_size:]            X_train = X_window[:train_size]    y_train = y_window[:train_size]    X_test = X_window[train_size:]    y_test = y_window[train_size:]      #LINEAR REGRESSION MODEL    model_linreg = LinearRegression().fit(X_train, y_train)    linreg_pred = model_linreg.predict(X_test)        #XGBOOST MODEL        param_grid_xgb = {'estimator__learning_rate': [0.01, 0.1, 0.2], 'estimator__max_depth': [3, 5, 7], 'estimator__subsample': [0.8, 0.9, 1.0]}            model_xgb = MultiOutputRegressor(xgboost.XGBRegressor())        #XGBoost hyperparameter tuning    grid_search_xgb = GridSearchCV(model_xgb, param_grid_xgb, cv=3, error_score='raise')    hyperparameters_tuning_xgb = grid_search_xgb.fit(X_train, y_train)    xgb_reg = hyperparameters_tuning_xgb.best_estimator_    xgb_pred = xgb_reg.predict(X_test)        #RANDOM FOREST MODEL    param_grid_rf = {'estimator__max_features': ['sqrt', 'log2', None],'estimator__max_depth': [3, 6, 9], 'estimator__max_leaf_nodes': [3, 6, 9]}         model_rf = MultiOutputRegressor(RandomForestRegressor())        #Random forest hyperparameter tuning    grid_search_rf = GridSearchCV(model_rf, param_grid_rf, cv=3, error_score='raise')    hyperparameters_tuning_rf = grid_search_rf.fit(X_train, y_train)    rf_reg = hyperparameters_tuning_rf.best_estimator_          rf_pred = rf_reg.predict(X_test)          #Reshaping data for RNN models    X_train_shaped = np.reshape(X_train_rnn, (X_train_rnn.shape[0], X_train_rnn.shape[1], feature_count))    X_test_shaped = np.reshape(X_test_rnn, (X_test_rnn.shape[0], X_test_rnn.shape[1], feature_count))    #LSTM MODEL    def lstm_model(hp):        lstm_model = Sequential()        lstm_model.add(Input(shape=(X_test_rnn.shape[1], feature_count)))        lstm_model.add(LSTM(hp.Choice('units', [8, 16, 32, 64])))        lstm_model.add(Dense(look_ahead, activation= "relu"))        learning_rate = hp.Choice('lr', [0.0001, 0.001, 0.01])        lstm_model.compile(loss='mean_squared_error', optimizer = Adam(learning_rate=learning_rate))        return lstm_model    #LSTM hyperparameter tuning    rsearch_lstm = RandomSearch(lstm_model, objective='val_loss', overwrite = True)        rsearch_lstm.search(X_train_shaped, y_train_rnn, epochs=25, validation_split = 0.3, verbose = 0)    best_hp = rsearch_lstm.get_best_hyperparameters()[0]    lstm_best_model = rsearch_lstm.get_best_models(num_models=1)    lstm_model = lstm_best_model[0]        lstm_pred = lstm_model.predict(X_test_shaped)        #BILSTM MODEL    def bi_lstm_model(hp):        bi_lstm_model = Sequential()        bi_lstm_model.add(Input(shape=(X_test_rnn.shape[1], feature_count)))        bi_lstm_model.add(Bidirectional(LSTM(hp.Choice('units', [8, 16, 32, 64]))))        bi_lstm_model.add(Dense(look_ahead, activation= "relu"))        learning_rate = hp.Choice('lr', [0.0001, 0.001, 0.01])        bi_lstm_model.compile(loss='mean_squared_error', optimizer = Adam(learning_rate=learning_rate))        return bi_lstm_model        #BiLSTM hyperparameter tuning    rsearch_bi_lstm = RandomSearch(bi_lstm_model, objective='val_loss', overwrite = True)    rsearch_bi_lstm.search(X_train_shaped, y_train_rnn, epochs=25, validation_split = 0.3, verbose = 0)    best_hp_bi = rsearch_bi_lstm.get_best_hyperparameters()[0]    bi_lstm_best_model = rsearch_bi_lstm.get_best_models(num_models=1)    bi_lstm_model = bi_lstm_best_model[0]        bi_lstm_pred = bi_lstm_model.predict(X_test_rnn)           #STACKED LSTM MODEL    def stacked_lstm_model(hp):                stacked_lstm_model = Sequential()        stacked_lstm_model.add(Input(shape=(X_test_rnn.shape[1], feature_count)))        stacked_lstm_model.add(LSTM(hp.Choice('units', [8, 16, 32, 64]), return_sequences=True))        stacked_lstm_model.add(Dropout(hp.Choice('dropout', [0.2, 0.3, 0.4])))        stacked_lstm_model.add(LSTM(hp.Choice('units_2', [4, 8, 16])))        stacked_lstm_model.add(Dense(look_ahead, activation= "relu"))        learning_rate = hp.Choice('lr', [0.0001, 0.001, 0.01])        stacked_lstm_model.compile(loss='mean_squared_error', optimizer = Adam(learning_rate=learning_rate))        return stacked_lstm_model        #Stacked LSTM hyperparameter tuning    rsearch_stacked_lstm = RandomSearch(stacked_lstm_model, objective='val_loss', overwrite = True)    rsearch_stacked_lstm.search(X_train_shaped, y_train_rnn, epochs=25, validation_split = 0.3, verbose = 0)    best_hp_stacked = rsearch_stacked_lstm.get_best_hyperparameters()[0]    stacked_lstm_best_model = rsearch_stacked_lstm.get_best_models(num_models=1)    stacked_lstm_model = stacked_lstm_best_model[0]        stacked_lstm_pred = stacked_lstm_model.predict(X_test_rnn)        #Retrieving the GCN model predictions for the station    y_test_gcn_station = []    gcn_pred_station = []    for g in range(y_test_GCN.shape[0]):        temp_ytest = []        temp_gcnpred = []        for t in range(i, 10 * look_ahead, 10):            temp_ytest.append(y_test_GCN[g][t])            temp_gcnpred.append(gcn_pred[g][t])         y_test_gcn_station.append(temp_ytest)        gcn_pred_station.append(temp_gcnpred)    #Unscaling the predictions     y_test_unscaled = []    y_test_rnn_unscaled = []    y_test_gcnstation_unscaled = []    linreg_pred_unscaled = []    xgb_pred_unscaled = []    rf_pred_unscaled = []    lstm_pred_unscaled = []    bi_lstm_pred_unscaled = []    stacked_lstm_pred_unscaled = []    gcn_pred_station_unscaled = []    for a in range(len(y_test)):        y_test_iter = []        y_test_rnn_iter = []        y_test_gcnstation_iter = []        linreg_pred_iter = []        xgb_pred_iter = []        rf_pred_iter = []        lstm_pred_iter = []        bi_lstm_pred_iter = []        stacked_lstm_iter = []        gcn_pred_station_iter = []        for b in range(look_ahead):            y_test_temp = scaler.inverse_transform(np.repeat(y_test[a][b], feature_count).reshape(1,feature_count))            y_test_iter.append(y_test_temp[0][0])            y_test_rnn_temp = scaler.inverse_transform(np.repeat(y_test_rnn[a][b], feature_count).reshape(1,feature_count))            y_test_rnn_iter.append(y_test_rnn_temp[0][0])             y_test_gcnstation_temp = scaler.inverse_transform(np.repeat(y_test_gcn_station[a][b], feature_count).reshape(1,feature_count))            y_test_gcnstation_iter.append(y_test_gcnstation_temp[0][0])            linreg_pred_temp = scaler.inverse_transform(np.repeat(linreg_pred[a][b], feature_count).reshape(1,feature_count))            linreg_pred_iter.append(linreg_pred_temp[0][0])            xgb_pred_temp = scaler.inverse_transform(np.repeat(xgb_pred[a][b], feature_count).reshape(1,feature_count))            xgb_pred_iter.append(xgb_pred_temp[0][0])            rf_pred_temp = scaler.inverse_transform(np.repeat(rf_pred[a][b], feature_count).reshape(1,feature_count))            rf_pred_iter.append(rf_pred_temp[0][0])            lstm_pred_temp = scaler.inverse_transform(np.repeat(lstm_pred[a][b], feature_count).reshape(1,feature_count))            lstm_pred_iter.append(lstm_pred_temp[0][0])            bi_lstm_pred_temp = scaler.inverse_transform(np.repeat(bi_lstm_pred[a][b], feature_count).reshape(1,feature_count))            bi_lstm_pred_iter.append(bi_lstm_pred_temp[0][0])            stacked_lstm_temp = scaler.inverse_transform(np.repeat(stacked_lstm_pred[a][b], feature_count).reshape(1,feature_count))            stacked_lstm_iter.append(stacked_lstm_temp[0][0])            gcn_pred_station_temp = scaler.inverse_transform(np.repeat(gcn_pred_station[a][b], feature_count).reshape(1,feature_count))            gcn_pred_station_iter.append(gcn_pred_station_temp[0][0])                                                     y_test_unscaled.append(y_test_iter)        y_test_rnn_unscaled.append(y_test_rnn_iter)        y_test_gcnstation_unscaled.append(y_test_gcnstation_iter)        linreg_pred_unscaled.append(linreg_pred_iter)        xgb_pred_unscaled.append(xgb_pred_iter)        rf_pred_unscaled.append(rf_pred_iter)        lstm_pred_unscaled.append(lstm_pred_iter)        bi_lstm_pred_unscaled.append(bi_lstm_pred_iter)        stacked_lstm_pred_unscaled.append(stacked_lstm_iter)        gcn_pred_station_unscaled.append(gcn_pred_station_iter)     #Obtaining the evalution metrics of each of the models    linreg_mae = mean_absolute_error(y_test_unscaled, linreg_pred_unscaled)    linreg_rmse = root_mean_squared_error(y_test_unscaled, linreg_pred_unscaled)    linreg_r2 = r2_score(y_test_unscaled, linreg_pred_unscaled)        xgb_mae = mean_absolute_error(y_test_unscaled, xgb_pred_unscaled)    xgb_rmse = root_mean_squared_error(y_test_unscaled, xgb_pred_unscaled)    xgb_r2 = r2_score(y_test_unscaled, xgb_pred_unscaled)           rf_mae = mean_absolute_error(y_test_unscaled, rf_pred_unscaled)    rf_rmse = root_mean_squared_error(y_test_unscaled, rf_pred_unscaled)    rf_r2 = r2_score(y_test_unscaled, rf_pred_unscaled)                lstm_mae = mean_absolute_error(y_test_rnn_unscaled, lstm_pred_unscaled)    lstm_rmse = root_mean_squared_error(y_test_rnn_unscaled, lstm_pred_unscaled)    lstm_r2 = r2_score(y_test_rnn_unscaled, lstm_pred_unscaled)        bi_lstm_mae = mean_absolute_error(y_test_rnn_unscaled, bi_lstm_pred_unscaled)    bi_lstm_rmse = root_mean_squared_error(y_test_rnn_unscaled, bi_lstm_pred_unscaled)    bi_lstm_r2 = r2_score(y_test_rnn_unscaled, bi_lstm_pred_unscaled)        stacked_lstm_mae = mean_absolute_error(y_test_rnn_unscaled, stacked_lstm_pred_unscaled)    stacked_lstm_rmse = root_mean_squared_error(y_test_rnn_unscaled, stacked_lstm_pred_unscaled)    stacked_lstm_r2 = r2_score(y_test_rnn_unscaled, stacked_lstm_pred_unscaled)        gcn_mae = mean_absolute_error(y_test_gcnstation_unscaled, gcn_pred_station_unscaled)    gcn_rmse = root_mean_squared_error(y_test_gcnstation_unscaled, gcn_pred_station_unscaled)    gcn_r2 = r2_score(y_test_gcnstation_unscaled, gcn_pred_station_unscaled)         #RMSE weights for ensemble model    rmse = [linreg_rmse, xgb_rmse, rf_rmse, lstm_rmse, bi_lstm_rmse, stacked_lstm_rmse, gcn_rmse]    rmse_weights = np.reciprocal(rmse)    rmse_weights =  [x / sum(rmse_weights) for x in rmse_weights]        #ENSEMBLE MODEL    ensemble_pred = []    for j in range(len(y_test)):        if look_ahead == 1:            pred = (linreg_pred_unscaled[j][0] * rmse_weights[0]) + (xgb_pred_unscaled[j][0] * rmse_weights[1]) + (rf_pred_unscaled[j][0] * rmse_weights[2]) + (lstm_pred_unscaled[j][0] * rmse_weights[3]) + (bi_lstm_pred_unscaled[j][0] * rmse_weights[4]) + (stacked_lstm_pred_unscaled[j][0] * rmse_weights[5]) + (gcn_pred_station_unscaled[j][0] * rmse_weights[6])        else:             pred_lists = [[x * rmse_weights[0] for x in linreg_pred_unscaled[j]], [x * rmse_weights[1] for x in xgb_pred_unscaled[j]], [x * rmse_weights[2] for x in rf_pred_unscaled[j]], [x * rmse_weights[3] for x in lstm_pred_unscaled[j]], [x * rmse_weights[4] for x in bi_lstm_pred_unscaled[j]], [x * rmse_weights[5] for x in stacked_lstm_pred_unscaled[j]], [x * rmse_weights[6] for x in gcn_pred_station_unscaled[j]]]                       pred = [sum(x) for x in zip(*pred_lists)]                ensemble_pred.append(pred)         final_pred.append(ensemble_pred)        #Ensemble model evaluation metrics    ensemble_mae = mean_absolute_error(y_test_unscaled, ensemble_pred)    ensemble_rmse = root_mean_squared_error(y_test_unscaled, ensemble_pred)    ensemble_r2 = r2_score(y_test_unscaled, ensemble_pred, multioutput = 'variance_weighted')         #Adding the results to the final dataframe    df_linreg = pd.DataFrame({'Model': 'Linear Regression', 'Station': StationsList[i], 'MAE': linreg_mae, 'RMSE': linreg_rmse, 'R2score': linreg_r2},index=[i])    df_xgb = pd.DataFrame({'Model': 'XGB Regressor', 'Station': StationsList[i], 'MAE': xgb_mae, 'RMSE': xgb_rmse, 'R2score': xgb_r2},index=[i])    df_rf = pd.DataFrame({'Model': 'RandomForest', 'Station': StationsList[i], 'MAE': rf_mae, 'RMSE': rf_rmse, 'R2score': rf_r2},index=[i])    df_lstm = pd.DataFrame({'Model': 'LSTM', 'Station': StationsList[i], 'MAE': lstm_mae, 'RMSE': lstm_rmse, 'R2score': lstm_r2},index=[i])    df_bi_lstm = pd.DataFrame({'Model': 'BiLSTM', 'Station': StationsList[i], 'MAE': bi_lstm_mae, 'RMSE': bi_lstm_rmse, 'R2score': bi_lstm_r2},index=[i])    df_stacked_lstm = pd.DataFrame({'Model': 'StackedLSTM', 'Station': StationsList[i], 'MAE': stacked_lstm_mae, 'RMSE': stacked_lstm_rmse, 'R2score': stacked_lstm_r2},index=[i])    df_gcn = pd.DataFrame({'Model': 'STGNN', 'Station': StationsList[i], 'MAE': gcn_mae, 'RMSE': gcn_rmse, 'R2score': gcn_r2},index=[i])    df_ensemble = pd.DataFrame({'Model': 'Ensemble', 'Station': StationsList[i], 'MAE': ensemble_mae, 'RMSE': ensemble_rmse, 'R2score': ensemble_r2},index=[i])    df_output = pd.concat([df_output,df_linreg])    df_output = pd.concat([df_output,df_xgb])    df_output = pd.concat([df_output,df_rf])    df_output = pd.concat([df_output,df_lstm])    df_output = pd.concat([df_output,df_bi_lstm])    df_output = pd.concat([df_output,df_stacked_lstm])    df_output = pd.concat([df_output,df_gcn])    df_output = pd.concat([df_output,df_ensemble])        print('Finished for station: ' + str(StationsList[i]))        #Creating plots of test data and predictions for each model    if look_ahead == 1:        date_values = df_i.index.values        test_dates = date_values[train_size + look_back:]            fig5, axs5 = plt.subplots(nrows=4, ncols=2, figsize=(12,12))        fig5.subplots_adjust(top = 0.9, bottom = 0.1, hspace = .3, wspace=.15)        fig5.suptitle(StationsList[i] + ': Lookback = ' + str(look_back) + ', Lookahead = ' + str(look_ahead) , fontsize = 'xx-large')        fig5.autofmt_xdate(rotation=45)                axs5[0,0].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[0,0].plot(test_dates, linreg_pred_unscaled, label = 'Prediction', color = 'lightblue')        axs5[0,0].set_xlabel('Date')        axs5[0,0].set_ylabel('PM2.5 Concentration')        axs5[0,0].set_title('Linear Regression')        axs5[0,0].legend()        axs5[0,1].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[0,1].plot(test_dates, rf_pred_unscaled, label = 'Prediction', color = 'lightblue')        axs5[0,1].set_xlabel('Date')        axs5[0,1].set_ylabel('PM2.5 Concentration')        axs5[0,1].set_title('Random Forest')        axs5[0,1].legend()                axs5[1,0].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[1,0].plot(test_dates, xgb_pred_unscaled, label = 'Prediction', color = 'lightblue')        axs5[1,0].set_xlabel('Date')        axs5[1,0].set_ylabel('PM2.5 Concentration')        axs5[1,0].set_title('XGBoost')        axs5[1,0].legend()        axs5[1,1].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[1,1].plot(test_dates, lstm_pred_unscaled, label = 'Prediction', color = 'lightblue')        axs5[1,1].set_xlabel('Date')        axs5[1,1].set_ylabel('PM2.5 Concentration')        axs5[1,1].set_title('LSTM')        axs5[1,1].legend()        axs5[2,0].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[2,0].plot(test_dates, bi_lstm_pred_unscaled, label = 'Prediction', color = 'lightblue')        axs5[2,0].set_xlabel('Date')        axs5[2,0].set_ylabel('PM2.5 Concentration')        axs5[2,0].set_title('BI-LSTM')        axs5[2,0].legend()        axs5[2,1].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[2,1].plot(test_dates, stacked_lstm_pred_unscaled, label = 'Prediction', color = 'lightblue')        axs5[2,1].set_xlabel('Date')        axs5[2,1].set_ylabel('PM2.5 Concentration')        axs5[2,1].set_title('Stacked LSTM')        axs5[2,1].legend()           axs5[3,0].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[3,0].plot(test_dates, gcn_pred_station_unscaled, label = 'Prediction', color = 'lightblue')        axs5[3,0].set_xlabel('Date')        axs5[3,0].set_ylabel('PM2.5 Concentration')        axs5[3,0].set_title('STGNN')        axs5[3,0].legend()                axs5[3,1].plot(test_dates, y_test_rnn_unscaled, label = 'Test Data', color = 'navy')        axs5[3,1].plot(test_dates, ensemble_pred, label = 'Prediction', color = 'lightblue')        axs5[3,1].set_xlabel('Date')        axs5[3,1].set_ylabel('PM2.5 Concentration')        axs5[3,1].set_title('Ensemble')        axs5[3,1].legend()                            plt.show()#Plot of the ensemble model performance for each of the stationsdf_ensemble_summary = df_output[df_output['Model'] == 'Ensemble'] print('')print('--------Ensemble SUMMARY TABLE-------')print('Lookback = ' + str(look_back) + ', Lookahead = ' + str(look_ahead) + ', With Wildfire Features= ' + str(wildfire_features))print(df_ensemble_summary)sns.barplot(x="Station", y="RMSE", data = df_ensemble_summary, color = 'cornflowerblue').set_title('Ensemble RMSE by Station, Lookback = ' + str(look_back) + ', Lookahead = ' + str(look_ahead))plt.xticks(rotation=70)plt.show()#Printing the final results tabledf_output_temp = df_output.drop(columns=['Station'])df_summary = df_output_temp.groupby(df_output_temp['Model'], sort=False).mean()df_summary = df_summary.reset_index() print('')print('--------SUMMARY TABLE-------')print('Lookback = ' + str(look_back) + ', Lookahead = ' + str(look_ahead) + ', With Wildfire Features= ' + str(wildfire_features))print(df_summary)#Accessing the 2021 mean predictions for mathematical optimization modelmean_2021 = []for s in range(len(final_pred)):    pred_2021 = final_pred[s][-365:]    mean_2021.append(np.mean(pred_2021))    print('Mean predictions for 2021 by station: ' + str(mean_2021))#Saving the predictions to a csvpd.DataFrame(final_pred).to_csv('predictions.csv')                                             