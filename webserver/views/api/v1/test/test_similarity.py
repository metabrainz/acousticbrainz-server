import os
import json
import unittest
import mock
import uuid

from webserver.testing import ServerTestCase
from webserver.views.api.v1 import similarity
from similarity.exceptions import IndexNotFoundException, ItemNotFoundException
from db.testing import TEST_DATA_PATH
from db.exceptions import NoDataFoundException


class APISimilarityViewsTestCase(ServerTestCase):

    def setUp(self):
        super(APISimilarityViewsTestCase, self).setUp()
        self.uuid = str(uuid.uuid4())

        self.test_recording1_mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        self.test_recording1_data_json = open(os.path.join(TEST_DATA_PATH, self.test_recording1_mbid + '.json')).read()
        self.test_recording1_data = json.loads(self.test_recording1_data_json)

        self.test_recording2_mbid = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_recording2_data_json = open(os.path.join(TEST_DATA_PATH, self.test_recording2_mbid + '.json')).read()
        self.test_recording2_data = json.loads(self.test_recording2_data_json)

    @mock.patch("similarity.utils.load_index_model")
    def test_get_similar_recordings_bad_uuid(self, load_index_model):
        """ URL Endpoint returns 404 because url-part doesn't match UUID.
            This error is raised by Flask, but we special-case to json.
        """
        resp = self.client.get("/api/v1/similarity/mfccs/nothing")
        self.assertEqual(404, resp.status_code)

        load_index_model.assert_not_called()
        expected_result = {"message": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."}
        self.assertEqual(resp.json, expected_result)

    @mock.patch("similarity.utils.load_index_model")
    @mock.patch("similarity.index_model.AnnoyIndex.get_nns_by_mbid")
    def test_get_similar_recordings_no_params(self, load_index_model, get_nns):
        """When offset, distance, n_trees, and n_neighbours are not specified,
        they are set with default values. Metric must be specified.
        """
        get_nns.return_value = {}
        metric = "mfccs"
        resp = self.client.get("/api/v1/similarity/%s/%s".format(metric, self.uuid))
        self.assertEqual(200, resp.status_code)

        offset = 0
        distance = "angular"
        n_trees = 10
        n_neighbours = 200
        load_index_model.assert_called_with(metric, distance, n_trees)
        get_nns.assert_called_with(self.uuid, offset, n_neighbours)

    @mock.patch("similarity.utils.load_index_model")
    @mock.patch("similarity.index_model.AnnoyIndex.get_nns_by_mbid")
    def test_get_similar_recordings_invalid_params(self, load_index_model, get_nns):
        get_nns.return_value = {}
        # If offset is not integer >= 0, APIBadRequest is raised
        resp = self.client.get("/api/v1/similarity/mfccs/%s?n=x" % self.uuid)
        self.assertEqual(400, resp.status_code)

        # If index params are not in index_model.BASE_INDICES, they default
        # If n_neighbours is larger than 1000, it defualts
        resp = self.client.get("/api/v1/similarity/mfccs/%s?n_trees=-1&distance_type=7&n_neighbours=2000" % self.uuid)
        self.assertEqual(200, resp.status_code)
        offset = 0
        distance = "angular"
        n_trees = 10
        n_neighbours = 200
        metric = "mfccs"
        load_index_model.assert_called_with(metric, distance, n_trees)
        get_nns.assert_called_with(self.uuid, offset, n_neighbours)

        # If n_neighbours is not numerical, it defaults
        resp = self.client.get("/api/v1/similarity/mfccs/%s?n_trees=-1&distance_type=7&n_neighbours=x" % self.uuid)
        self.assertEqual(200, resp.status_code)
        load_index_model.assert_called_with(metric, distance, n_trees)
        get_nns.assert_called_with(self.uuid, offset, n_neighbours)

    @mock.patch("similarity.utils.load_index_model")
    def test_get_similar_recordings_invalid_metric(self, load_index_model):
        # If metric does not exist, APIBadRequest is raised
        resp = self.client.get("/api/v1/similarity/nothing/%s" % self.uuid)
        self.assertEqual(404, resp.status_code)
        load_index_model.assert_not_called()
        expected_result = {"message": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."}
        self.assertEqual(expected_result, resp.json)

    @mock.patch("similarity.utils.load_index_model")
    @mock.patch("similarity.index_model.AnnoyIndex.get_nns_by_mbid")
    def test_get_similar_recordings_index_errors(self, load_index_model, get_nns):
        # If index does not load with given parameters, APIBadRequest is raised
        load_index_model.side_effect = IndexNotFoundException
        resp = self.client.get("/api/v1/similarity/mfccs/%s" % self.uuid)
        self.assertEqual(400, resp.status_code)
        expected_result = {"message": "Index does not exist with specified parameters."}
        self.assertEqual(expected_result, resp.json)

        # If the (MBID, offset) combination is not submitted, APIBadRequest is raised
        get_nns.side_effect = NoDataFoundException
        resp = self.client.get("/api/v1/similarity/mfccs/%s?n=2" % self.uuid)
        self.assertEqual(400, resp.status_code)
        expected_result = {"message": "No submission exists for the given (MBID, offset) combination."}
        self.assertEqual(expected_result, resp.json)

        # If the (MBID, offset) is submitted but not yet indexed, APIBadRequest is raised
        get_nns.side_effect = ItemNotFoundException
        resp = self.client.get("/api/v1/similarity/mfccs/%s?n=2" % self.uuid)
        self.assertEqual(400, resp.status_code)
        expected_result = {"message": "The submission of interest is not indexed."}
        self.assertEqual(expected_result, resp.json)


class SimilarityValidationTest(unittest.TestCase):

    def test_check_index_params(self):
        # If metric does not exist, APIBadRequest is raised.
        metric = "x"
        with self.assertRaises(webserver.views.api.exceptions.APIBadRequest) as ex:
            similarity._check_index_params(metric)
        self.assertEqual(str(ex.exception), {"message": "An index with the specified metric does not exist."})
