import struct
import umap
import numpy as np
import pandas as pd
import logging
from helpers import *
from rasterfairy import coonswarp
import rasterfairy

class DimensionReductor:
    def __init__(self, n_neighbors=15, min_dist=0.1, n_components=2, metric='euclidean', cache=None):
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.n_components = n_components
        self.metric = metric
        self.cache = cache
        self.logger = logging.getLogger('umaper')
        self.umap = umap.UMAP(n_neighbors=self.n_neighbors, min_dist=self.min_dist, n_components=self.n_components,
                              metric=self.metric)

    def fit(self, X):
        self.umap.fit(X)

    def transform(self, X):
        return self.umap.transform(X)

    # @duration
    def fit_transform(self, X):
        self.logger.info('Fit UMAP')
        X = np.array(X)
        self.logger.info('X shape: {}'.format(X.shape))
        embeddings = self.umap.fit_transform(X)
        return embeddings
    
    def saveToCsv(self, X, path, ids, name = "umap"):
        dataframe = pd.DataFrame(data=X, columns=['x', 'y'])
        dataframe['id'] = ids
        dataframe.set_index('id')
        dataframe.to_csv("{}/{}.csv".format(path, name), index=False)
        self.logger.info("Saved embedding to {}".format(path))

if __name__ == "__main__":
    umap = DimensionReductor(n_neighbors=2, min_dist=0.1)
    features = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [7, 8, 9], [7, 8, 9], [7, 1, 9], [7, 8, 9], [7, 8, 9], [1, 8, 9]]
    features = np.array(features)
    embedding = umap.fit_transform(features)
    # print(embedding)
    # umap = np.array((embedding + 1)/2)
    # print(umap)
    # umap = coonswarp.rectifyCloud(umap,
    #   perimeterSubdivisionSteps=4,
    #   autoPerimeterOffset=False,
    #   paddingScale=1.05)
    # pos = rasterfairy.transformPointCloud2D(umap)[0]

    # print(pos)
