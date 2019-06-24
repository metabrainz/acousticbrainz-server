import os

import similarity.exceptions

from annoy import AnnoyIndex
from sqlalchemy import text

class AnnoyModel(object):
    def __init__(self, connection, metric_name, n_trees=10, distance_type='angular', load_existing=False):
        """
        Args:
            - connection: a connection to the database that will be used by an
              instance of the index.
            - metric_name: the name of the metric that vectors in the index will
              represent, a string.
            - n_trees: the number of trees used in building the index, a positive
              integer.
            - distance_type: distance measure, a string. Possibilities are
              "angular", "euclidean", "manhattan", "hamming", or "dot".
            - load_existing: if load_existing is True, then load function will be
              called upon initialization.
        """
        self.connection = connection
        self.metric_name = metric_name
        self.n_trees = n_trees
        self.distance_type = distance_type
        self.dimension = self.get_vector_dimension()
        self.index = AnnoyIndex(self.dimension, metric=self.distance_type)

        # in_loaded_state set to True if the index is built, loaded, or saved.
        # At any of these points, items can no longer be added to the index.
        self.in_loaded_state = False
        if load_existing:
            self.load()
