import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from sklearn.metrics import silhouette_score, calinski_harabaz_score
from sklearn.metrics.pairwise import euclidean_distances
from .Metrics.dunn_index import dunn
from .Metrics.davies_bouldin_index import compute_DB_index

class ClusterMetric:

    def __init__(self, name :str, plus_minus_one: bool, greater_is_better: bool):
        self.name = name
        self.plus_minus_one = plus_minus_one
        self.greater_is_better = greater_is_better


class ClusterMetrics:

    def __init__(self, cluster_class, cluster_nr_range, plot=True, **kwargs):

        self.cluster_class = cluster_class
        self.cluster_nr_range = cluster_nr_range
        self.plot = plot
        self.cluster_kwargs = kwargs

        self.metric_dict = {}
        self.SILHOUETTE = ClusterMetric("silhouette_score", True, True)
        self.CH_SCORE = ClusterMetric("calinski_harabaz_score", False, True)
        self.DUNN_INDEX = ClusterMetric("dunn_index", True, True)
        self.DB_INDEX = ClusterMetric("davies_bouldin_index", False, False)
        self.INERTIA = ClusterMetric("inertia", False, False)
        self.metric_list = [self.SILHOUETTE, self.CH_SCORE, self.DUNN_INDEX, self.DB_INDEX, self.INERTIA]


    def fit(self, X):

        # for each intended cluster size
        for nr_clusters in self.cluster_nr_range:

            cluster_obj = self.cluster_class(n_clusters=nr_clusters, **self.cluster_kwargs)
            cluster_labels = cluster_obj.fit_predict(X)

            if len(self.metric_dict) == 0:
                for item in self.metric_list:
                    self.metric_dict[item.name] = []

            # 1. Silhouette Score -> greater is better
            silhouette_avg = silhouette_score(X, cluster_labels)
            self.metric_dict[self.SILHOUETTE.name].append(silhouette_avg)

            # 2. Calinski Harabaz Score -> greater is better
            ch_score = calinski_harabaz_score(X, cluster_labels)
            self.metric_dict[self.CH_SCORE.name].append(ch_score)

            # 3. Dunn Index -> greater is better
            dunk = dunn(cluster_labels, euclidean_distances(X))
            self.metric_dict[self.DUNN_INDEX.name].append(dunk)

            # 4. Davies Bouldin Index -> lower is better
            centroids = cluster_obj.cluster_centers_
            db_index = compute_DB_index(X, cluster_labels, centroids, nr_clusters)
            self.metric_dict[self.DB_INDEX.name].append(db_index)

            # 5. Kmeans inertia
            self.metric_dict[self.INERTIA.name].append(cluster_obj.inertia_)

        if self.plot:

            cols = 3
            rows = int(np.ceil(len(self.metric_list)/3))
            cnt = 1

            fig = plt.figure()
            # handles_list = []
            for key, value in self.metric_dict.items():
                metric = [i for i in self.metric_list if i.name == key][0]
                ax = fig.add_subplot(rows, cols, cnt)
                ith_color = cm.spectral(float(cnt) / len(self.cluster_nr_range))
                handle_x, = ax.plot(self.cluster_nr_range, value, label=key, color=ith_color)
                ax.set_ylabel(key)
                ax.set_xlabel("number of clusters")
                # ax.set_ylim([-1, 1])
                # handle_x, = ax2.plot(self.cluster_nr_range, value, label=key)
                # handles_list.append(handle_x)
                cnt += 1
            # plt.legend(handles=handles_list)
            plt.tight_layout()
            plt.show()

        debug = True


