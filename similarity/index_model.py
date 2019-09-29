import os

import similarity.exceptions
import db.similarity
import db.data
import db.exceptions

from annoy import AnnoyIndex
from collections import defaultdict


class AnnoyModel(object):
    def __init__(self, metric_name, n_trees=10, distance_type='angular', load_existing=False):
        """
        Args:
            - metric_name: the name of the metric that vectors in the index will
              represent, a string.
            - n_trees: the number of trees used in building the index, a positive
              integer.
            - distance_type: distance measure, a string. Possibilities are
              "angular", "euclidean", "manhattan", "hamming", or "dot".
            - load_existing: if load_existing is True, then load function will be
              called upon initialization.
        """
        # Check params
        self.parse_initial_params(metric_name, n_trees, distance_type)
        self.dimension = db.similarity.get_metric_dimension(self.metric_name)
        self.index = AnnoyIndex(self.dimension, metric=self.distance_type)

        # in_loaded_state set to True if the index is built, loaded, or saved.
        # At any of these points, items can no longer be added to the index.
        self.in_loaded_state = False
        if load_existing:
            self.load()

    def parse_initial_params(self, metric_name, n_trees, distance_type):
        # Validate the index parameters passed to AnnoyModel.
        if metric_name in BASE_INDICES:
            self.metric_name = metric_name
        else:
            raise similarity.exceptions.IndexNotFoundException('Index for specified metric is not possible.')

        if distance_type in BASE_INDICES[self.metric_name]:
            self.distance_type = distance_type
        else:
            raise similarity.exceptions.IndexNotFoundException('Index for specified distance_type is not possible.')

        if n_trees in BASE_INDICES[self.metric_name][self.distance_type]:
            self.n_trees = n_trees
        else:
            raise similarity.exceptions.IndexNotFoundException('Index for specified number of trees is not possible.')

    def build(self):
        """Build and load the index using the specified number of trees. An index
        must be built before it can be queried."""
        self.index.build(self.n_trees)
        self.in_loaded_state = True

    def save(self, location=os.path.join(os.getcwd(), 'annoy_indices'), name=None):
        # Save and load the index using the metric name.
        if not self.in_loaded_state:
            raise similarity.exceptions.LoadStateException('Index must be built before saving.')
        try:
            os.makedirs(location)
        except OSError:
            if not os.path.isdir(location):
                raise
        name = '_'.join([name or self.metric_name, self.distance_type, str(self.n_trees)]) + '.ann'
        file_path = os.path.join(location, name)
        self.index.save(file_path)

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
        except IOError:
            raise similarity.exceptions.IndexNotFoundException

    def add_recording_by_mbid(self, mbid, offset):
        """Add a single recording specified by (mbid, offset) to the index.
        Note that when adding a single recording, space is allocated for
        the lowlevel.id + 1 items.
        """
        if self.in_loaded_state:
            raise similarity.exceptions.CannotAddItemException("Item cannot be added once index is in load state.")
        item = db.similarity.get_similarity_row_mbid(mbid, offset)
        if item:
            recording_vector = item[self.metric_name]
            id = item['id']
            # If an item already exists, this should not error
            # and we should not add the item.
            try:
                self.index.get_item_vector(id)
            except IndexError:
                self.index.add_item(id, recording_vector)

    def add_recording_by_id(self, id):
        """Add a single recording specified by its lowlevel.id to the index.
        Note that when adding a single recording, space is allocated for
        lowlevel.id + 1 items.
        """
        if self.in_loaded_state:
            raise similarity.exceptions.CannotAddItemException("Item cannot be added once index is in load state.")
        item = db.similarity.get_similarity_row_id(id)
        if item:
            # If an item already exists, this should not error
            # and we should not add the item.
            try:
                self.index.get_item_vector(id)
            except IndexError:
                self.index.add_item(item["id"], item[self.metric_name])

    def add_recording_with_vector(self, id, vector):
        """Add a single recording to the index using its lowlevel.id and
        a precomputed metric vector.
        
        Args:
            id: non-negative integer lowlevel.id for a recording.
            
            vector: metric vector (list) corresponding to the lowlevel.id.
            Dimension of the vector must match the dimension with which the
            index is initialized
        
        *NOTE*: Annoy will allocate memory for max(n) + 1 items.
        """
        if self.in_loaded_state:
            raise similarity.exceptions.CannotAddItemException("Item cannot be added once index is in load state.")
        if not len(vector) = index.dimension:
            raise similarity.exceptions.CannotAddItemException("Dimension of vector provided does not match index dimension.")

        self.index.add_item(id, vector)

    def get_nns_by_id(self, id, num_neighbours):
        """Get the most similar recordings for a recording with the
           specified id.

        Args:
            id: non-negative integer lowlevel.id for a recording.

            num_neighbours: positive integer, number of similar recordings
            to be returned in the query.

            eval_info: boolean, determines whether or not eval info (lowlevel.ids and distances)
            should be returned for each similar recording.

            return_distances: boolean, determines where or not distance between the
            query recording and each similar recording should be included.

        Returns:
            A list of the form [<lowlevel.ids>, <recordings>, <distances>]
            where <lowlevel.ids> is a list of lowlevel.ids [id_1, ..., id_n],
            <recordings> is a list of tuples (MBID, offset),
            and <distances> is a list of distances, corresponding to each similar recording.
        """
        try:
            items = self.index.get_nns_by_item(id, num_neighbours, include_distances=True)
        except IndexError:
            raise similarity.exceptions.ItemNotFoundException('The item you are requesting is not indexed.')

        # Unpack to get ids and distances
        ids = items[0]
        distances = items[1]
        recordings = db.data.get_mbids_by_ids(ids)
        return ids, recordings, distances

    def get_nns_by_mbid(self, mbid, offset, num_neighbours):
        # Find corresponding lowlevel.id to (mbid, offset) combination,
        # then call get_nns_by_id
        id = db.data.get_lowlevel_id(mbid, offset)
        return self.get_nns_by_id(id, num_neighbours)

    def get_bulk_nns_by_mbid(self, recordings, num_neighbours, extended_info=False):
        """Get most similar recordings for each (MBID, offset) tuple provided.
        Similar recordings list returned is ordered with the most similar at
        index 0.

        Arguments:
            recordings: a list of tuples of form (MBID, offset), for which
            similar recordings will be found

            num_neighbours: an integer, the number of similar recordings desired
            for each recording specified.

            extended_info: boolean, whether or not lowlevel.id and distance
            should be returned alongside (MBID, offset) of a similar recording.

        Returns:
            if extended_info = True, list of similar recordings 
            contains tuples of the form (lowlevel.id, (MBID, offset), distance)

                {"mbid1": {"offset1": [similar_rec_1, ..., similar_rec_n],
                           ...,
                           "offsetn": [similar_rec_1, ..., similar_rec_n]
                          },
                 ...,
                 "mbidn": {"offset1": [similar_rec_1, ..., similar_rec_n],
                           ...,
                           "offsetn": [similar_rec_1, ..., similar_rec_n]
                          }
                }

            if extended_info = False, a list of (MBID, offset) tuples:

                {"mbid1": {"offset1": [(MBID, offset), ..., (MBID, offset)],
                           ...,
                           "offsetn": [(MBID, offset), ..., (MBID, offset)]
                          },
                 ...,
                 "mbidn": {"offset1": [(MBID, offset), ..., (MBID, offset)],
                           ...,
                           "offsetn": [(MBID, offset), ..., (MBID, offset)]
                          }
                }
        """
        recordings_info = defaultdict(dict)
        for mbid, offset in recordings:
            try:
                ids, similar_recordings, distances = self.get_nns_by_mbid(mbid, offset, num_neighbours)
                if extended_info:
                    recordings_info[mbid][str(offset)] = list(zip(ids, similar_recordings, distances))
                else:
                    recordings_info[mbid][str(offset)] = similar_recordings
            except (similarity.exceptions.ItemNotFoundException, db.exceptions.NoDataFoundException):
                continue

        return recordings_info

    def get_similarity_between(self, rec_one, rec_two):
        """Get the distance of the similarity measure between
        two recordings.

        Args:
            rec_one and rec_two are tuples of the form (MBID, offset)

        Returns:
            Distance between two recordings, of type float.
            If an IndexError occurs (one or more of ids is not indexed)
            then None is returned.
        """
        id_1 = db.data.get_lowlevel_id(rec_one[0], rec_one[1])
        id_2 = db.data.get_lowlevel_id(rec_two[0], rec_two[1])
        try:
            return self.index.get_distance(id_1, id_2)
        except IndexError:
            return None


"""
A dictionary to track the base indices that should be built.
Naming convention for a saved index is "<metric_name>_<distance_type>_<n_trees>.ann"
e.g. "mfccs_angular_10.ann"
Format of BASE_INDICES dictionary:
{"metric_name": {"distance_type": [n_trees, ..., n_trees]}
"""
BASE_INDICES = {
    "mfccs": {"angular": [10]},
    "mfccsw": {"angular": [10]},
    "gfccs": {"angular": [10]},
    "gfccsw": {"angular": [10]},
    "key": {"angular": [10]},
    "bpm": {"angular": [10]},
    "onsetrate": {"angular": [10]},
    "moods": {"angular": [10]},
    "instruments": {"angular": [10]},
    "dortmund": {"angular": [10]},
    "rosamerica": {"angular": [10]},
    "tzanetakis": {"angular": [10]}
}
