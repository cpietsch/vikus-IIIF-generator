import umap
import numpy as np

class Umaper:
    def __init__(self, n_neighbors=15, min_dist=0.1, n_components=2, metric='euclidean'):
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.n_components = n_components
        self.metric = metric
        self.umap = umap.UMAP(n_neighbors=self.n_neighbors, min_dist=self.min_dist, n_components=self.n_components,
                              metric=self.metric)

    def fit(self, X):
        self.umap.fit(X)

    def transform(self, X):
        return self.umap.transform(X)

    def fit_transform(self, X):
        return self.umap.fit_transform(X)


if __name__ == "__main__":
    umap = Umaper(n_neighbors=2, min_dist=0.1)
    features = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [7, 8, 9], [7, 8, 9], [7, 1, 9], [7, 8, 9], [7, 8, 9], [1, 8, 9]]
    features = np.array(features)
    embedding = umap.fit_transform(features)
    print(embedding)