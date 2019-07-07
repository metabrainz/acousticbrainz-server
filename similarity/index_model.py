import os

from similarity.metrics import BASE_METRICS
import similarity.exceptions
import db.data
import db.exceptions

from annoy import AnnoyIndex
from sqlalchemy import text
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
        with db.engine.connect() as connection:
            result = connection.execute("""
                SELECT *
                  FROM similarity
                 LIMIT 1
            """)
            try:
                dimension = len(result.fetchone()[self.metric_name])
                return dimension
            except (ValueError, TypeError):
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
        except FileNotFoundError:
            raise similarity.exceptions.IndexNotFoundException

    def add_recording_by_mbid(self, mbid, offset):
        """Add a single recording specified by (mbid, offset) to the index.
        Note that when adding a single recording, space is allocated for
        the lowlevel.id + 1 items.
        """
        if self.in_loaded_state:
            raise similarity.exceptions.CannotAddItemException

        with db.engine.connect() as connection:
            query = text("""
                SELECT *
                  FROM similarity
                 WHERE id = (
                    SELECT id
                      FROM lowlevel
                     WHERE gid = :mbid
                       AND submission_offset = :offset )
            """)
            result = connection.execute(query, { "mbid": mbid, "submission_offset": offset})
            row = result.fetchone()
            if row:
                recording_vector = row[self.metric_name]
                id = row['id']
                if not self.index.get_item_vector(id):
                    self.index.add_item(id, recording_vector)

    def add_recording_by_id(self, id):
        """Add a single recording specified by its lowlevel.id to the index.
        Note that when adding a single recording, space is allocated for
        lowlevel.id + 1 items.
        """
        if self.in_loaded_state:
            raise similarity.exceptions.CannotAddItemException

        with db.engine.connect() as connection:
            query = text("""
                SELECT *
                  FROM similarity
                 WHERE id = :id
            """)
            result = connection.execute(query, {"id": id})
            if not result.rowcount:
                raise similarity.exceptions.ItemNotFoundException
            row = result.fetchone()
            if not self.index.get_item_vector(id):
                self.index.add_item(row[id], row[self.metric_name])

    def add_recording_with_vector(self, id, vector):
        if self.in_loaded_state:
            raise similarity.exceptions.CannotAddItemException
        # If an item already exists, this should not error
        # and we should not add the item.
        try:
            self.index.get_item_vector(id)
        except IndexError:
            self.index.add_item(id, vector)

    def get_nns_by_id(self, id, num_neighbours, return_ids=False):
        """Get the most similar recordings for a recording with the
           specified id.

        Args:
            id: non-negative integer lowlevel.id for a recording.

            num_neighbours: positive integer, number of similar recordings
            to be returned in the query.

            return_ids: boolean, determines whether (mbid, offset), or lowlevel.id
            is returned for each similar recording.

        Returns:
            If return_ids = True: A list of lowlevel.ids [id1, ..., idn]
            If return_ids = False: A list of tuples [(mbid1, offset), ..., (mbidn, offset)]
        """
        try:
            ids = self.index.get_nns_by_item(id, num_neighbours)
        except IndexError:
            raise similarity.exceptions.ItemNotFoundException
        if return_ids:
            # Return only ids
            return ids
        else:
            # Get corresponding (mbid, offset) for the most similar ids
            with db.engine.connect() as connection:
                query = text("""
                    SELECT id
                         , gid
                         , submission_offset
                      FROM lowlevel
                     WHERE id IN :ids
                """)
                result = connection.execute(query, {"ids": tuple(ids)})

                recordings = []
                for row in result.fetchall():
                    recordings.append((row["gid"], row["submission_offset"]))

                return recordings

    def get_nns_by_mbid(self, mbid, offset, num_neighbours, return_ids=False):
        # Find corresponding lowlevel.id to (mbid, offset) combination,
        # then call get_nns_by_id
        mbid = mbid.lower()
        with db.engine.connect() as connection:
            query = text("""
                SELECT id
                  FROM lowlevel
                 WHERE gid = :mbid
                   AND submission_offset = :offset
            """)
            result = connection.execute(query, {"mbid": mbid, "offset": offset})
            if not result.rowcount:
                raise db.exceptions.NoDataFoundException('That (mbid, offset) combination does not exist')
            else:
                id = result.fetchone()[0]
                return self.get_nns_by_id(id, num_neighbours, return_ids)

    def get_bulk_nns_by_mbid(self, recordings, num_neighbours, return_ids=False):
        """Get most similar recordings for each (MBID, offset) tuple provided.
        Similar recordings list returned is ordered with the most similar at
        index 0.

        Arguments:
            recordings: a list of tuples of form (MBID, offset), for which
            similar recordings will be found

            num_neighbours: an integer, the number of similar recordings desired
            for each recording specified.

            return_ids: boolean, determines whether lowlevel.id or (MBID, offset)
            should be returned for similar recordings.

        Returns:
            if return_ids = True, a list of similar lowlevel.ids:

                {"mbid1": {"offset1": [similar_lowlevel.ids],
                           ...,
                           "offsetn": [similar_lowlevel.ids]
                          },
                 ...,
                 "mbidn": {"offset1": [similar_lowlevel.ids],
                           ...,
                           "offsetn": [similar_lowlevel.ids]
                          }
                }

            if return_ids = False, a list of (MBID, offset) tuples:

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
                similar_recordings = self.get_nns_by_mbid(id, num_neighbours, return_ids)
                recordings_info[mbid][offset] = similar_recordings
            except similarity.exceptions.ItemNotFoundException:
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
