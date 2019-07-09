import copy
import json
import os.path

import mock

import db.similarity
import db.exceptions
from db.testing import DatabaseTestCase, TEST_DATA_PATH, gid_types
import similarity.metrics
import similarity.utils


class SimilarityDBTestCase(DatabaseTestCase):

    def setUp(self):
        super(SimilarityDBTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

        self.test_mbid_two = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_lowlevel_data_json_two = open(os.path.join(TEST_DATA_PATH, self.test_mbid_two + '.json')).read()
        self.test_lowlevel_data_two = json.loads(self.test_lowlevel_data_json_two)

    def test_count_similarity(self):
        # Write lowlevel then submit similarity
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        self.assertEqual(1, db.similarity.count_similarity())
        # Submit exact same data, no change
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        self.assertEqual(1, db.similarity.count_similarity())

        # make a copy of the data and change it
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]
        db.data.submit_low_level_data(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 1)
        self.assertEqual(2, db.similarity.count_similarity())

    def test_submit_similarity_by_id_none(self):
        """If id cannot be cast as an integer, a ValueError should be raised.

        If lowlevel is not submitted, a NoDataFoundException should be raised.
        """
        id = 'test'
        with self.assertRaises(db.exceptions.BadDataException):
            db.similarity.submit_similarity_by_id(id)

        id = 100
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity.submit_similarity_by_id(100)

    @mock.patch("db.similarity.insert_similarity")
    @mock.patch("db.data.check_for_submission")
    @mock.patch("similarity.utils.init_metrics")
    def test_submit_similarity_by_id_init_metrics(self, init_metrics, check_for_submission, insert_similarity):
        """Check that when called with a list of metrics, init_metrics is
        not called. If data is not submitted for a metric, then isnan is
        True for that metric, and the vector should be [None, ..., None]"""
        # Init metrics
        onset = mock.Mock()
        onset.name = "onset"
        onset.get_data.return_value = [1.23, 12.10, 3.29]
        onset.transform.side_effect = ValueError
        onset.length.return_value = 3

        mfccs = mock.Mock()
        mfccs.name = "mfccs"
        mfccs.get_data.return_value = {"means": [1, 2, 3, 4, 5, 6]}
        mfccs.transform.return_value = [1.66, 2.44]
        mfccs.length.return_value = 2
        metrics = [onset, mfccs]
        # init_metrics.return_value = [onset, mfccs]
        vectors_info = [("onset", [None, None, None], True),
                        ("mfccs", [1.66, 2.44], False)]

        id = 0
        check_for_submission.return_value = True
        db.similarity.submit_similarity_by_id(id, metrics)

        init_metrics.assert_not_called()
        insert_similarity.assert_called_with(id, vectors_info)

    @mock.patch("db.similarity.insert_similarity")
    @mock.patch("db.data.check_for_submission")
    @mock.patch("similarity.utils.init_metrics")
    def test_submit_similarity_by_id_no_metrics(self, init_metrics, check_for_submission, insert_similarity):
        """Check that when called with a list of metrics, init_metrics is
        not called. If data is not submitted for a metric, then isnan is
        True for that metric, and the vector should be [None, ..., None]"""
        # Init metrics
        onset = mock.Mock()
        onset.name = "onset"
        onset.get_data.return_value = [1.23, 12.10, 3.29]
        onset.transform.side_effect = ValueError
        onset.length.return_value = 3

        mfccs = mock.Mock()
        mfccs.name = "mfccs"
        mfccs.get_data.return_value = {"means": [1, 2, 3, 4, 5, 6]}
        mfccs.transform.return_value = [1.66, 2.44]
        mfccs.length.return_value = 2
        init_metrics.return_value = [onset, mfccs]
        vectors_info = [("onset", [None, None, None], True),
                        ("mfccs", [1.66, 2.44], False)]

        id = 0
        check_for_submission.return_value = True
        db.similarity.submit_similarity_by_id(id)

        init_metrics.assert_called_once()
        insert_similarity.assert_called_with(id, vectors_info)

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
