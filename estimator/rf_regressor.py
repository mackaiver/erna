import pandas as pd
import click
from sklearn import ensemble
from sklearn import cross_validation
from sklearn import linear_model
from sklearn2pmml import sklearn2pmml

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
plt.style.use('ggplot')
# from IPython import embed
import numpy as np
from sklearn_pandas import DataFrameMapper

training_variables = ['ConcCore', 'Concentration_onePixel', 'Concentration_twoPixel','Leakage',
        'Leakage2',  'Size', 'Slope_long', 'Slope_spread', 'Slope_spread_weighted',
       'Slope_trans','Timespread',
       'Timespread_weighted', 'Width', 'ZdPointing',
       'arrTimePosShower_kurtosis', 'arrTimePosShower_max',
       'arrTimePosShower_mean', 'arrTimePosShower_min',
       'arrTimePosShower_skewness', 'arrTimePosShower_variance',
       'arrTimeShower_kurtosis', 'arrTimeShower_max', 'arrTimeShower_mean',
       'arrTimeShower_min', 'arrTimeShower_skewness',
       'arrTimeShower_variance', 'arrivalTimeMean', 'concCOG', 'm3l',
       'm3t', 'maxPosShower_kurtosis', 'maxPosShower_max',
       'maxPosShower_mean', 'maxPosShower_min', 'maxPosShower_skewness',
       'maxPosShower_variance', 'maxSlopesPosShower_kurtosis',
       'maxSlopesPosShower_max', 'maxSlopesPosShower_mean',
       'maxSlopesPosShower_min', 'maxSlopesPosShower_skewness',
       'maxSlopesPosShower_variance', 'maxSlopesShower_kurtosis',
       'maxSlopesShower_max', 'maxSlopesShower_mean',
       'maxSlopesShower_min', 'maxSlopesShower_skewness',
       'maxSlopesShower_variance', 'numIslands', 'numPixelInShower',
       'phChargeShower_kurtosis', 'phChargeShower_max',
       'phChargeShower_mean', 'phChargeShower_min',
       'phChargeShower_skewness', 'phChargeShower_variance',
       'photonchargeMean']

@click.command()
@click.argument('path', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('out', type=click.Path(exists=False, dir_okay=False, file_okay=True) )
@click.option('--n_trees','-n', default=100,  help='Number of trees to train.')
@click.option('--n_jobs','-j', default=1,  help='Number of trees to train.')
@click.option('--n_sample','-s', default=-1,  help='Number of data rows to sample. -1 for all rows.')
@click.option('--n_cv','-c', default=5,  help='Number of CV folds to perform')
@click.option('--bins','-b', default=100,  help='number of bins in ocrrelation plot.')
@click.option('--log','-l', is_flag=True,  help='Flags whether a log function should be applied to the true energie and size before training stuff.')
@click.option('--max_depth','-d', default=None, type=click.INT, help='Maximum depth of the trees in the forest.')
@click.option('--save','-sm', is_flag=True,  help='Flags whether model should be save to pmml.')
def main(path, out, n_trees, n_jobs,n_sample, n_cv,  bins, log, max_depth, save):
    '''
    Train a RF regressor and write the model to OUT in pmml format.
    '''
    print("Loading data")

    df = pd.read_hdf(path, key='table')

    if n_sample > 0:
        df = df.sample(n_sample)

    df_target = df['MCorsikaEvtHeader.fTotalEnergy']
    df_target.name = 'estimated_energy'
    df_train = df[training_variables]
    df_train = df_train.dropna(axis=0, how='any')
    df_target = df_target[df_train.index]

    if log:
        df_target = df_target.apply(np.log10)
        df_train['Size'] = df_train['Size'].apply(np.log10)

    rf = ensemble.ExtraTreesRegressor(n_estimators=n_trees,max_features="sqrt", n_jobs=n_jobs, max_depth=max_depth)
    # rf = linear_model.Ridge()
    print("Training classifier in a {} fold CV...".format(n_cv))
    scores = cross_validation.cross_val_score(rf, df_train, df_target, cv=n_cv)

    print("Cross validated R^2 scores: {}".format(scores))
    print("Mean R^2 score : %0.2f (+/- %0.2f)" % (scores.mean(), scores.std()))

    print("Building new model on complete data set...")
    # rf = ensemble.ExtraTreesRegressor(n_estimators=n_trees,max_features="sqrt", oob_score=True, n_jobs=n_jobs, max_depth=max_depth)
    rf.fit(df_train, df_target)
    print("Score on complete data set: {}".format(rf.score(df_train, df_target)))
    #
    # importances = pd.DataFrame(rf.feature_importances_, index=df_train.columns, columns=['importance'])
    # importances = importances.sort_values(by='importance', ascending=True)
    # print('Plotting importances to importances.pdf')
    # ax = importances.plot(
    #     kind='barh',
    #     color='#2775d0'
    # )
    # ax.set_xlabel(u'feature importance')
    # ax.get_yaxis().grid(None)
    # plt.tight_layout()
    # plt.savefig('importances.pdf')

    print('Plotting correlation to correlation.pdf')
    fig = plt.figure()
    prediction = rf.predict(df_train)

    if log:
        _, _, _, im = plt.hist2d(df_target, prediction, bins=bins, normed=True, cmin=1, cmap='inferno')
    else:
        _, _, _, im = plt.hist2d(np.log10(df_target), np.log10(prediction), bins=bins, normed=True, cmin=1, cmap='inferno')

    fig.colorbar(im)
    plt.xlabel('logarithm of true energy')
    plt.ylabel('logarithm of estimated energy')
    plt.tight_layout()
    plt.savefig('correlation.pdf')

    print("Saving prediction to prediction.json")
    result = pd.DataFrame()
    result['Estimated Energy'] = prediction
    result['True Energy'] = df_target.values

    result.to_json('prediction.json')

    if save:
        print("writing model to {}".format(out))
        mapper = DataFrameMapper([
                                (list(df_train.columns), None),
                                ('estimated_energy', None)
                        ])
        sklearn2pmml(rf, mapper,  out)

if __name__ == '__main__':
    main()
