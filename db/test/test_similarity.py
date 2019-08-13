import copy
import json
import os.path
import mock
import unittest

import db
import db.similarity
import db.exceptions
from db.testing import DatabaseTestCase, TEST_DATA_PATH, gid_types
import similarity.utils

from sqlalchemy import text


class SimilarityDBTestCase(DatabaseTestCase):

    def setUp(self):
        super(SimilarityDBTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

        self.test_highlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '_highlevel.json')).read()
        self.test_highlevel_data = json.loads(self.test_highlevel_data_json)
        self.test_highlevel_models_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '_highlevel_models.json')).read()
        self.test_highlevel_models = json.loads(self.test_highlevel_models_json)

        self.test_mbid_two = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_lowlevel_data_json_two = open(os.path.join(TEST_DATA_PATH, self.test_mbid_two + '.json')).read()
        self.test_lowlevel_data_two = json.loads(self.test_lowlevel_data_json_two)

    def test_count_similarity(self):
        # Write lowlevel then submit similarity
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.similarity_stats.compute_stats(1)
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        self.assertEqual(1, db.similarity.count_similarity())
        # Submit exact same data, no change
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        self.assertEqual(1, db.similarity.count_similarity())

        # make a copy of the data and change it
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]
        db.data.submit_low_level_data(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        db.similarity_stats.compute_stats(2)
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 1)
        self.assertEqual(2, db.similarity.count_similarity())

    def test_submit_similarity_by_id_none(self):
        """If id cannot be cast as an integer, a ValueError should be raised."""
        id = 'test'
        with self.assertRaises(db.exceptions.BadDataException):
            db.similarity.submit_similarity_by_id(id)

    def test_submit_similarity_by_id_no_hl(self):
        """When called with a list of metrics, similarity vectors are submitted 
        for each metric in the list. If data is not submitted for a metric, the 
        vector should be [0, ..., 0].
        
        If no data is passed as an argument, data is collected before submission
        and vectors should still be successfully inserted.

        If no database connection is passed as an argument, one is still created 
        before the insertion.
        """
        # Submitted lowlevel, but not highlevel.
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.similarity_stats.compute_stats(1)
        id = db.data.get_lowlevel_id(self.test_mbid, 0)
        metrics = similarity.utils.init_metrics()
        db.similarity.submit_similarity_by_id(id, metrics=metrics)

        # High level metrics have empty vectors.
        expected_vectors = ([-809.079956055, 196.693603516, 14.5762844086, 6.08403015137, 0.968960940838, -4.33947467804, -6.33537626266, -1.52541470528, -1.90009725094, -4.04138422012, -9.53146743774, -6.10197162628, -1.44469249249],
                            [-809.079956055, 186.8589233402, 13.1550966787615, 5.21629535103085, 0.789224742318431, -3.3578027846313, -4.65708371473948, -1.06525398070688, -1.26056333770978, -2.54708001920098, -5.70684164012272, -3.4708020240964, -0.780654161887449],
                            [-169.202331543, 164.232177734, -89.7964019775, -10.2318019867, -47.1032066345, -6.18469190598, -33.0790672302, -3.90048241615, -20.4164390564, -8.5227022171, -15.5154972076, -4.24216938019, -5.64954137802],
                            [-169.202331543, 156.0205688473, -81.0412527846937, -8.77249122834691, -38.3658561988417, -4.78559670115787, -24.3161540703592, -2.72385234395541, -13.5446828041837, -5.37142804158589, -9.28970130884004, -2.41294633490444, -3.05278667428058],
                            [0.5, 0.866025403784439],
                            [0.69130100170388, 0.722566900046779],
                            [0.823196082996991, 0.567757174272955],
                            [0.0, 0.0, 0.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        with db.engine.connect() as connection:
            query = text("""
                SELECT *
                  FROM similarity.similarity
                 WHERE id = :id
            """)
            result = connection.execute(query, {"id": id})
            row = result.fetchone()
            # All metric columns should contain vectors
            vectors = row[1:]

        self.assertEqual(expected_vectors, vectors)

    def test_submit_similarity_by_id(self):
        """Check that when called with no metrics, vectors are still created
        for all base metrics.
        
        If data is passed as an argument, it is not collected. If all low and 
        highlevel data are present, no vectors should be of the form [0, ..., 0].
        """
        # Submit low and highlevel data.
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.similarity_stats.compute_stats(1)
        id = db.data.get_lowlevel_id(self.test_mbid, 0)
        build_sha = "test"
        db.data.write_high_level(self.test_mbid, id, self.test_highlevel_data, build_sha)

        data = (self.test_lowlevel_data, self.test_highlevel_models)
        db.similarity.submit_similarity_by_id(id, data=data)
        expected_vectors = [[-809.079956055, 196.693603516, 14.5762844086, 6.08403015137, 0.968960940838, -4.33947467804, -6.33537626266, -1.52541470528, -1.90009725094, -4.04138422012, -9.53146743774, -6.10197162628, -1.44469249249],
                            [-809.079956055, 186.8589233402, 13.1550966787615, 5.21629535103085, 0.789224742318431, -3.3578027846313, -4.65708371473948, -1.06525398070688, -1.26056333770978, -2.54708001920098, -5.70684164012272, -3.4708020240964, -0.780654161887449],
                            [-169.202331543, 164.232177734, -89.7964019775, -10.2318019867, -47.1032066345, -6.18469190598, -33.0790672302, -3.90048241615, -20.4164390564, -8.5227022171, -15.5154972076, -4.24216938019, -5.64954137802],
                            [-169.202331543, 156.0205688473, -81.0412527846937, -8.77249122834691, -38.3658561988417, -4.78559670115787, -24.3161540703592, -2.72385234395541, -13.5446828041837, -5.37142804158589, -9.28970130884004, -2.41294633490444, -3.05278667428058],
                            [0.5, 0.866025403784439],
                            [0.69130100170388, 0.722566900046779],
                            [0.823196082996991, 0.567757174272955],
                            [0.0581060945988, 0.953247070312, 0.0500397793949, 0.995198726654, 0.0156338009983],
                            [0.988367855549, 0.0248921476305, 0.965500116348],
                            [0.00316655938514, 0.00568170007318, 0.114020898938, 0.0338333025575, 0.509120285511, 0.0465195141733, 0.0925819277763, 0.0783302634954, 0.116745553911],
                            [0.00617602840066, 0.195983037353, 0.0784998983145, 0.0032169369515, 0.00680347532034, 0.663908660412, 0.0344416685402, 0.010970310308], [0.154698759317, 0.311486542225, 0.0707420706749, 0.0773398503661, 0.0344257615507, 0.0618693865836, 0.0442127361894, 0.0775808021426, 0.0620644688606, 0.10557962954]]

        with db.engine.connect() as connection:
            query = text("""
                SELECT *
                  FROM similarity.similarity
                 WHERE id = :id
            """)
            result = connection.execute(query, {"id": id})
            row = result.fetchone()
            # All metric columns should contain vectors
            vectors = row[1:]

        self.assertEqual(tuple(expected_vectors), vectors)

    def test_submit_similarity_by_mbid_none(self):
        # If no submission exists, NoDataFoundException should be raised.
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)

    @mock.patch("db.data.get_lowlevel_id")
    @mock.patch("db.similarity.submit_similarity_by_id")
    def test_submit_similarity_by_mbid(self, submit_similarity_by_id, get_lowlevel_id):
        # Check that lowlevel.id is found and passed to submit_similarity_by_id
        get_lowlevel_id.return_value = 0
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        get_lowlevel_id.assert_called_with(self.test_mbid, 0)
        submit_similarity_by_id.assert_called_with(0)
