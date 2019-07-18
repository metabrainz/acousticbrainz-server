import os
import json

import db
from db.testing import DatabaseTestCase, TEST_DATA_PATH
from db import gid_types
import db.similarity
import db.similarity_stats

from sqlalchemy import text

class SimilarityStatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(SimilarityStatsDatabaseTestCase, self).setUp()

        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

    def test_calculate_stats_for_feature(self):
        # If nothing is in the database, avg and stddev should be None
        path = "data->'lowlevel'->'gfcc'->'mean'->>2"
        mean, stddev = db.similarity_stats.calculate_stats_for_feature(path)
        self.assertEqual(mean, None)
        self.assertEqual(stddev, None)

        # With only one submission in the database, mean should be the
        # value of the submission, stddev should be 0
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        id = db.data.get_lowlevel_id(self.test_mbid, 0)
        db.similarity.submit_similarity_by_id(id)
        mean, stddev = db.similarity_stats.calculate_stats_for_feature(path)
        self.assertEqual(mean, -89.7964019775)
        self.assertEqual(stddev, 0)

    def test_check_global_stats(self):
        # Submit similarity data, verify global stats
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        id = db.data.get_lowlevel_id(self.test_mbid, 0)
        db.similarity.submit_similarity_by_id(id)
        means, stddevs = db.similarity_stats.check_global_stats("gfccs")
        # Only one recording, mean is equal to gfccs of its data
        self.assertEqual(means, [
            -169.202331543,
            164.232177734,
            -89.7964019775,
            -10.2318019867,
            -47.1032066345,
            -6.18469190598,
            -33.0790672302,
            -3.90048241615,
            -20.4164390564,
            -8.5227022171,
            -15.5154972076,
            -4.24216938019,
            -5.64954137802
        ])
        self.assertEqual(stddevs, [0] * len(stddevs))

    def test_insert_delete_similarity_stats(self):
        # Check that similarity stats can be correctly inserted and deleted
        metric = "gfccs"
        means = [
            -169.202331543,
            164.232177734,
            -89.7964019775,
            -10.2318019867,
            -47.1032066345,
            -6.18469190598,
            -33.0790672302,
            -3.90048241615,
            -20.4164390564,
            -8.5227022171,
            -15.5154972076,
            -4.24216938019,
            -5.64954137802
        ]
        stddevs = [0] * len(means)
        db.similarity_stats.insert_similarity_stats(metric, means, stddevs)
        query = text("""
            SELECT *
              FROM similarity_stats
             WHERE metric = :metric
        """)
        with db.engine.connect() as connection:
            result = connection.execute(query, {"metric": metric})
            row = result.fetchone()
            self.assertEqual(row["means"], means)
            self.assertEqual(row["stddevs"], stddevs)
        db.similarity_stats.delete_similarity_stats(metric)
        with db.engine.connect() as connection:
            result = connection.execute(query, {"metric": metric})
            self.assertEqual(result.rowcount, 0)