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

    def get_vector_dimension(self):
        """
        Get dimension of metric vectors. If there is no metric of this type
        already created then we need to raise an error.
        """
        result = self.connection.execute("""
            SELECT *
              FROM similarity
             LIMIT 1
        """)
        try:
            dimension = len(result.fetchone()[self.metric_name])
            return dimension
        except ValueError:
            raise similarity.exceptions.IndexNotFoundException("No existing metric named \"{}\"".format(self.metric_name))

    def build(self):
        self.index.build(self.n_trees)
        self.in_loaded_state = True

    def save(self, location=os.path.join(os.getcwd(), 'annoy_indices'), name=None):
        # Save and load the index using the metric name.
        try: 
            os.makedirs(location)
        except OSError:
            if not os.path.isdir(location):
                raise
        name = '_'.join([name or self.metric_name, self.distance_type, str(self.n_trees)]) + '.ann'
        file_path = os.path.join(location, name)
        self.index.save(file_path)
        self.in_loaded_state = True

    def load(self, name=None):
        """
        Args:
            name: name of the metric that should be loaded. If None, it will use the
            metric specified when initializing the index.
        Raises:
            IndexNotFoundException: if there is no saved index with the given parameters.
        """
        # Load and build an existing annoy index.
        file_path = os.path.join(os.getcwd(), 'annoy_indices')
        name = '_'.join([name or self.metric_name, self.distance_type, str(self.n_trees)]) + '.ann'
        full_path = os.path.join(file_path, name)
        try:
            self.index.load(full_path)
            self.in_loaded_state = True
        # Need to add specific exception here.
        except:
            raise similarity.exceptions.IndexNotFoundException
