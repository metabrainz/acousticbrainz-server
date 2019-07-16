import os
import json
import mock
import unittest

from db.testing import DatabaseTestCase, TEST_DATA_PATH
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
        self.model.save()
        expected_path = "/code/annoy_indices/mfccs_angular_10.ann"
        self.assertEqual(True, os.path.isfile(expected_path))

    def test_save_location(self):
        # Saves to specified location with specified name, with params appended
        self.model.build()
        self.model.save(location="/code/annoy_indices/test_indices", name="test_mfccs")
        expected_path = "/code/annoy_indices/test_indices/test_mfccs_angular_10.ann"
        self.assertEqual(True, os.path.isfile(expected_path))

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
