import os
import json
import mock

import db
from webserver.testing import AcousticbrainzTestCase, DB_TEST_DATA_PATH
from db import gid_types
import db.similarity
import db.similarity_stats
import similarity.metrics


class SimilarityStatsDatabaseTestCase(AcousticbrainzTestCase):

    def setUp(self):
        super(SimilarityStatsDatabaseTestCase, self).setUp()

        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(DB_TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

    @mock.patch("db.similarity_stats.insert_similarity_stats")
    @mock.patch("db.similarity_stats.get_random_sample_lowlevel")
    def test_compute_stats(self, get_random_sample_lowlevel, insert_similarity_stats):
        # Check that insert_similarity_stats is called correctly
        sample_size = 2
        get_random_sample_lowlevel.return_value = [[(1.0, 3.0), (1.0, 3.0), (2.0, 5.0), (2.0, 5.0)],
                                                   [(2.0, 6.0), (2.0, 6.0), (4.0, 10.0), (4.0, 10.0)]]
        db.similarity_stats.compute_stats(sample_size)

        # Same feature path for weighted and unweighted MFCC/GFCC
        features = ["data->'lowlevel'->'gfcc'->'mean'",
                    "data->'lowlevel'->'gfcc'->'mean'",
                    "data->'lowlevel'->'mfcc'->'mean'",
                    "data->'lowlevel'->'mfcc'->'mean'"]
        get_random_sample_lowlevel.assert_called_with(sample_size, features)

        means = [[1.5, 4.5], [1.5, 4.5], [3.0, 7.5], [3.0, 7.5]]
        stddevs = [[0.5, 1.5], [0.5, 1.5], [1.0, 2.5], [1.0, 2.5]]
        metric_names = ["gfccsw", "gfccs", "mfccs", "mfccsw"]
        insert_similarity_stats.assert_called_with(metric_names, means, stddevs)

    def test_get_random_sample_lowlevel(self):
        # Without any lowlevel submissions, sample cannot be collected
        sample_size = 10
        features = ["data->'lowlevel'->'gfcc'->'mean'",
                    "data->'lowlevel'->'gfcc'->'mean'",
                    "data->'lowlevel'->'mfcc'->'mean'",
                    "data->'lowlevel'->'mfcc'->'mean'"]
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity_stats.get_random_sample_lowlevel(sample_size, features)

        # With sample size < 1% of submissions, error is raised
        sample_size = 0.001
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity_stats.get_random_sample_lowlevel(sample_size, features)

    def test_assign_stats(self):
        """If means and stddevs are not both attributes,
        nothing will be assigned."""
        metric = similarity.metrics.KeyMetric()
        db.similarity_stats.assign_stats(metric)
        # No means or stddevs assigned
        self.assertEqual(hasattr(metric, "means"), False)
        self.assertEqual(hasattr(metric, "stddevs"), False)

    def test_assign_stats_none(self):
        # With no stats calculated, error is raised.
        metric = similarity.metrics.MfccsMetric()
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity_stats.assign_stats(metric)
