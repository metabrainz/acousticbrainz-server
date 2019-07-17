import os
import json
import mock
import unittest

import db.exceptions
from db.testing import DatabaseTestCase, TEST_DATA_PATH, gid_types
import similarity.exceptions
from similarity.index_model import AnnoyModel


class IndexModelTestCase(DatabaseTestCase):

    @mock.patch("db.similarity.get_metric_dimension")
    def setUp(self, get_metric_dimension):
        super(IndexModelTestCase, self).setUp()
        # Init model with valid params
        metric = "mfccs"
        n_trees = 10
        distance_type = "angular"
        get_metric_dimension.return_value = 3
        self.model = AnnoyModel(metric, n_trees, distance_type)

        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

        self.test_mbid_two = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_lowlevel_data_json_two = open(os.path.join(TEST_DATA_PATH, self.test_mbid_two + '.json')).read()
        self.test_lowlevel_data_two = json.loads(self.test_lowlevel_data_json_two)

    @mock.patch("similarity.index_model.os")
    def test_save_errors(self, os):
        # If index has not been built, LoadStateException raised.
        with self.assertRaises(similarity.exceptions.LoadStateException):
            self.model.save()

        # If there is an issue creating a directory in the location given,
        # and the directory does not already exist, error is raised.
        self.model.build()
        os.makedirs.side_effect = OSError
        os.path.isdir.return_value = False
        with self.assertRaises(OSError):
            self.model.save()

    def test_save(self):
        # If location is correct, assert saved with proper file name
        # and full path
        self.model.build()
        self.model.index = mock.Mock()
        self.model.save()
        expected_path = "/code/annoy_indices/mfccs_angular_10.ann"
        self.model.index.save.assert_called_with(expected_path)

    def test_save_location(self):
        # Saves to specified location with specified name, with params appended
        self.model.build()
        self.model.index = mock.Mock()
        self.model.save(location="/code/annoy_indices/test_indices", name="test_mfccs")
        expected_path = "/code/annoy_indices/test_indices/test_mfccs_angular_10.ann"
        self.model.index.save.assert_called_with(expected_path)

    def test_load(self):
        # Raises error if no index with specified name exists
        name = "test"
        with self.assertRaises(similarity.exceptions.IndexNotFoundException):
            self.model.load(name=name)

        # No name specified, uses metric name
        self.model.index = mock.Mock()
        self.model.load()
        expected_path = "/code/annoy_indices/mfccs_angular_10.ann"
        self.model.index.load.assert_called_with(expected_path)
        self.assertEqual(True, self.model.in_loaded_state)

    @mock.patch("db.similarity.get_similarity_row_mbid")
    def test_add_recording_by_mbid_no_submission(self, get_similarity_row_mbid):
        # If model is built, (in_loaded_state is True), error is raised.
        self.model.in_loaded_state = True
        with self.assertRaises(similarity.exceptions.CannotAddItemException):
            self.model.add_recording_by_mbid(self.test_mbid, 0)

        # If recording and metrics data are not submitted, no addition occurs.
        get_similarity_row_mbid.return_value = None
        self.model.index = mock.Mock()
        self.model.in_loaded_state = False
        self.model.add_recording_by_mbid(self.test_mbid, 0)
        self.model.index.get_item_vector.assert_not_called()

    @mock.patch("db.similarity.get_similarity_row_mbid")
    def test_add_recordings_by_mbid_exists(self, get_similarity_row_mbid):
        # If item with given lowlevel.id already exists, no addition occurs.
        self.model.index = mock.Mock()
        self.model.index.get_item_vector.return_value = [1, 2, 3]
        get_similarity_row_mbid.return_value = {"id": 1, "mfccs": "data"}
        
        self.model.add_recording_by_mbid(self.test_mbid, 0)
        self.model.index.add_item.assert_not_called()

    @mock.patch("db.similarity.get_similarity_row_id")
    def test_add_recordings_by_id_none(self, get_similarity_row_id):
        # If model is built, (in_loaded_state is True), error is raised.
        self.model.in_loaded_state = True
        with self.assertRaises(similarity.exceptions.CannotAddItemException):
            self.model.add_recording_by_id(1)

        # If recording and metrics data are not submitted, no addition occurs
        get_similarity_row_id.return_value = None
        self.model.index = mock.Mock()
        self.model.in_loaded_state = False

        self.model.add_recording_by_id(1)
        self.model.index.get_item_vector.assert_not_called()

    @mock.patch("db.similarity.get_similarity_row_id")
    def test_add_recordings_by_id_exists(self, get_similarity_row_id):
        # If item with given lowlevel.id already exists, no addition occurs.
        self.model.index = mock.Mock()
        self.model.index.get_item_vector.return_value = [1, 2, 3]
        get_similarity_row_id.return_value = {"id": 1, "mfccs": "data"}

        self.model.add_recording_by_id(1)
        self.model.index.add_item.assert_not_called()

    @mock.patch("db.similarity.get_similarity_row_id")
    def test_add_recordings_by_id(self, get_similarity_row_id):
        # If item is not already submitted, addition occurs.
        get_similarity_row_id.return_value = {"id": 1, "mfccs": "data"}
        self.model.in_loaded_state = False
        self.model.index = mock.Mock()
        self.model.index.get_item_vector.side_effect = IndexError

        self.model.add_recording_by_id(1)
        self.model.index.add_item.assert_called_with(1, "data")

    def test_add_recording_with_vector_none(self):
        # If model is built, (in_loaded_state is True), error is raised.
        self.model.in_loaded_state = True
        id = 1
        vector = [1, 2, 3]
        with self.assertRaises(similarity.exceptions.CannotAddItemException):
            self.model.add_recording_with_vector(id, vector)
        
        # If item is already submitted, no addition occurs.
        self.model.in_loaded_state = False
        self.model.index = mock.Mock()
        self.model.index.get_item_vector.return_value = vector

        self.model.add_recording_with_vector(1, vector)
        self.model.index.add_item.assert_not_called()

    def test_add_recording_with_vector(self):
        # If no item is already submitted, addition occurs.
        self.model.in_loaded_state = False
        vector = [1, 2, 3]
        self.model.index = mock.Mock()
        self.model.index.get_item_vector.side_effect = IndexError

        self.model.add_recording_with_vector(1, vector)
        self.model.index.add_item.assert_called_with(1, vector)

    def test_get_nns_by_id_none(self):
        # If item is not submitted, error is raised
        id = 1
        n_neighbours = 2
        self.model.index = mock.Mock()
        self.model.index.get_nns_by_item.side_effect = IndexError
        with self.assertRaises(similarity.exceptions.ItemNotFoundException):
            self.model.get_nns_by_id(id, n_neighbours)

    @mock.patch("db.data.get_mbids_by_ids")
    def test_get_nns_by_id_return_ids(self, get_mbids_by_ids):
        # If return_ids is True, list of lowlevel.ids is returned.
        id = 1
        n_neighbours = 2
        self.model.index = mock.Mock()
        expected = [1, 2]
        self.model.index.get_nns_by_item.return_value = expected

        self.assertEqual(expected, self.model.get_nns_by_id(id, n_neighbours, return_ids=True))

        # If return_ids is False, list of (MBID, offset) tuples is returned.
        expected = [(self.test_mbid, 1), (self.test_mbid, 2)]
        get_mbids_by_ids.return_value = expected
        self.assertEqual(expected, self.model.get_nns_by_id(id, n_neighbours, return_ids=False))

    def test_get_bulk_nns_by_mbid(self):
        """
        If an item is not indexed, ItemNotFoundException caught and item
        is skipped.

        If a recording is not submitted, NoDataFoundException caught and item
        is skipped.
        """
        num_neighbours = 2
        recordings = [(self.test_mbid, 0), (self.test_mbid, 1), (self.test_mbid, 2)]
        returns = [similarity.exceptions.ItemNotFoundException,
                   db.exceptions.NoDataFoundException,
                   [(self.test_mbid, 2), (self.test_mbid, 5)]]
        self.model.get_nns_by_mbid = mock.Mock()
        self.model.get_nns_by_mbid.side_effect = returns

        expected = {self.test_mbid: {'2': [(self.test_mbid, 2), (self.test_mbid, 5)]}}
        ret = self.model.get_bulk_nns_by_mbid(recordings, num_neighbours)
        self.assertDictEqual(expected, ret)
        
    def test_get_similarity_between_none(self):
        # If one of the (MBID, offset) tuples is not submitted,
        # error is raised.
        rec1 = (self.test_mbid, 0)
        rec2 = (self.test_mbid_two, 0)
        with self.assertRaises(db.exceptions.NoDataFoundException):
            self.model.get_similarity_between(rec1, rec2)
        
        # If one of the (MBID, offset) tuples is not indexed,
        # None is returned.
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.submit_low_level_data(self.test_mbid_two, self.test_lowlevel_data_two, gid_types.GID_TYPE_MBID)
        self.model.index = mock.Mock()
        self.model.index.get_distance.side_effect = IndexError

        self.assertEqual(None, self.model.get_similarity_between(rec1, rec2))

    def test_get_similarity_between(self):
        # If (MBID, offset) tuples are submitted and indexed,
        # distance measure from Annoy is returned.
        rec1 = (self.test_mbid, 0)
        rec2 = (self.test_mbid_two, 0)

        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.submit_low_level_data(self.test_mbid_two, self.test_lowlevel_data_two, gid_types.GID_TYPE_MBID)

        self.model.index = mock.Mock()
        self.model.index.get_distance.return_value = 2.0
        
        self.assertEqual(2.0, self.model.get_similarity_between(rec1, rec2))


class IndexModelValidationTestCase(unittest.TestCase):

    @mock.patch("similarity.index_model.AnnoyModel.load")
    @mock.patch("db.similarity.get_metric_dimension")
    def test_parse_params(self, get_metric_dimension, load):
        get_metric_dimension.return_value = 3
        # If metric does not exist, IndexNotFoundError on initialization
        metric = "mfc"
        n_trees = 10
        distance = "angular"
        with self.assertRaises(similarity.exceptions.IndexNotFoundException):
            model = AnnoyModel(metric, n_trees=n_trees, distance_type=distance)
            # load_existing defaults to False
            model.load.assert_not_called()

        # Invalid n_trees
        metric = "mfccs"
        n_trees = -1
        distance = "angular"
        with self.assertRaises(similarity.exceptions.IndexNotFoundException):
            model = AnnoyModel(metric, n_trees=n_trees, distance_type=distance)
            model.load.assert_not_called()

        # Invalid distance_type
        metric = "mfccs"
        n_trees = 10
        distance = "x"
        with self.assertRaises(similarity.exceptions.IndexNotFoundException):
            model = AnnoyModel(metric, n_trees=n_trees, distance_type=distance)
            model.load.assert_not_called()

        # Load existing False, existing params
        metric = "mfccs"
        n_trees = 10
        distance = "angular"
        model = AnnoyModel(metric, n_trees=n_trees, distance_type=distance)
        model.load.assert_not_called()

        # Load existing False, existing params
        metric = "mfccs"
        n_trees = 10
        distance = "angular"
        model = AnnoyModel(metric, n_trees=n_trees, distance_type=distance, load_existing=True)
        model.load.assert_called()
