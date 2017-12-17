import networkx as nx

import csv, os, pickle
import pandas as pd

import numpy as np

import sklearn
from sklearn.model_selection import KFold
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import LinearRegression, Lasso

from sklearn.metrics import r2_score

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from deep_stuff import deep_mlp
from keras.callbacks import ModelCheckpoint
from keras.models import load_model


root_dir = 'E:/brains/graphs/'
targets_file_1 = 'Templeton114.csv'
targets_file_2 = 'Templeton255.csv'


graphtypes = ['AAL', 'desikan', 'CPAC200']
rois = [116, 70, 200]


df1 = pd.read_csv(root_dir + targets_file_1, index_col=0)
df2 = pd.read_csv(root_dir + targets_file_2)

n_subjects = 114
n_outputs = 8

ursis = []
graph_features = []

# label_col = df1.loc['URSI']
# print('label col:')
# print(label_col)

ursi_ids = df1.iloc[:, 0]

pls = PLSRegression()
linreg = LinearRegression(normalize=True)
lasso = Lasso(fit_intercept=True, normalize=True)

classifiers = [pls, linreg, lasso]
classifier_names = ['LR', 'PLS', 'Lasso']

r = {}
for graphtype in graphtypes:
    r[graphtype] = {}
    for name in classifier_names:
        r[graphtype][name] = []

    r[graphtype]['deep'] = []

for graphtype, n_roi in zip(graphtypes, rois):
    print('Running analysis for: ', graphtype)

    # y = df1.iloc[:, 1:11].as_matrix()

    # x = np.zeros((n_subjects, (n_roi * n_roi // 2) + (n_roi // 2)), dtype='float32')
    x = np.zeros((n_subjects, n_roi), dtype='float32')
    y = np.zeros((n_subjects, n_outputs), dtype='float32')
    
    for i, graph_filename in enumerate(os.listdir(root_dir + graphtype)):

        ursi = graph_filename[4:13]
        ursis.append(ursi)

        try:
            targets = np.hstack((df1.loc[ursi, 'CCI'], df1.loc[ursi, :].iloc[4:].as_matrix()))
            y[i, :] = targets

            graph_data = np.load(root_dir + graphtype + '/' + graph_filename)
            # print('graph shape:', graph_data.shape)

            g = nx.Graph(graph_data)

            # rich_coeff = nx.rich_club_coefficient()

            features = np.sum(graph_data, axis=0)

            # x[i, :] = graph_data[np.triu_indices(n_roi)]
            x[i, :] = features

            # print('nans:', np.sum(np.isnan(graph_data)))
            # print(np.max(x[i, :]), np.min(x[i, :]), np.mean(x[i, :]))

        except KeyError as e:
            print(e)
            i -= 1

    # print(i, 'subjects')


    kf = KFold(n_splits=10)

    print('x:', x.shape)
    print('y:', y.shape)

    for train_index, test_index in kf.split(range(x.shape[0])):
        x_train = x[train_index]
        y_train = y[train_index]
        x_test = x[test_index]
        y_test = y[test_index]

        # print('nans:', np.sum(np.isnan(x_train)))
        # print('infs:', np.sum(np.isinf(x_train)))
        #
        # print('nans:', np.sum(np.isnan(y_train)))
        # print('infs:', np.sum(np.isinf(y_train)))


        model_checkpoint = ModelCheckpoint(root_dir + 'best_model.hdf5', monitor="val_loss", verbose=0, save_best_only=True, save_weights_only=False, mode='min')

        model = deep_mlp(n_roi)
        model.compile('adam', 'mse', metrics=['accuracy'])
        model.fit(x_train, y_train, epochs=1000, validation_split=0.1, callbacks=[model_checkpoint])

        model.load_weights(root_dir + 'best_model.hdf5')

        predictions = model.predict(x_test)
        actual = y_test

        r2 = r2_score(actual, predictions)
        r[graphtype]['deep'].append(r2)

        for classifier, name in zip(classifiers, classifier_names):
            classifier.fit(x_train, y_train)
            r[graphtype][name].append(classifier.score(x_test, y_test))


for graphtype in graphtypes:
    print('Parcelation:', graphtype)
    for name in classifier_names + ['deep']:
        print(name, np.mean(r[graphtype][name]), np.std(r[graphtype][name]))

scores = []
score_labels = []


for graphtype in graphtypes:
    for name in classifier_names + ['deep']:
        scores.append(r[graphtype][name])
        score_labels.append(name)


plt.figure(figsize=(12, 9))
bplot = plt.boxplot(scores, patch_artist=True, zorder=3)

plt.xticks(np.arange(1, len(scores)+1), score_labels, rotation=0, horizontalalignment='center', fontsize=20)
plt.grid(zorder=0)
plt.xlim(0, len(scores) + 1)
plt.ylim(0, 1)

colors = ['pink', 'red', 'darkred', 'firebrick', 'pink', 'red', 'darkred', 'firebrick', 'pink', 'red', 'darkred', 'firebrick']

for patch, color in zip(bplot['boxes'], colors):
    patch.set_facecolor(color)

plt.xlabel('Classifier', fontsize=24)
plt.ylabel('$r^2$', fontsize=24)
plt.tight_layout()

results_dir = root_dir
plt.savefig(results_dir + 'metrics_boxplot.png')