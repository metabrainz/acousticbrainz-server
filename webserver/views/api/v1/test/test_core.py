from __future__ import absolute_import
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import db.exceptions
import mock
import uuid
import os
import json


class CoreViewsTestCase(ServerTestCase):

    def setUp(self):
        super(CoreViewsTestCase, self).setUp()
        self.uuid = str(uuid.uuid4())

        self.test_recording1_mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        self.test_recording1_data_json = open(os.path.join(TEST_DATA_PATH, self.test_recording1_mbid + '.json')).read()
        self.test_recording1_data = json.loads(self.test_recording1_data_json)

        self.test_recording2_mbid = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_recording2_data_json = open(os.path.join(TEST_DATA_PATH, self.test_recording2_mbid + '.json')).read()
        self.test_recording2_data = json.loads(self.test_recording2_data_json)
        
    def test_get_low_level(self):
        mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        resp = self.client.get("/api/v1/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get("/api/v1/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 200)

    def test_submit_low_level(self):
        mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"

        with open(os.path.join(TEST_DATA_PATH, mbid + ".json")) as json_file:
            with self.app.test_client() as client:
                sub_resp = client.post("/api/v1/%s/low-level" % mbid,
                                       data=json_file.read(),
                                       content_type="application/json")
                self.assertEqual(sub_resp.status_code, 200)

        resp = self.client.get("/api/v1/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 200)

    def test_cors_headers(self):
        mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.load_low_level_data(mbid)

        resp = self.client.get("/api/v1/%s/low-level" % mbid)
        self.assertEqual(resp.headers["Access-Control-Allow-Origin"], "*")

        # TODO: Test in get_high_level.

    @mock.patch("db.data.load_low_level")
    def test_ll_bad_uuid(self, ll):
        resp = self.client.get("/api/v1/nothing/low-level")
        self.assertEqual(404, resp.status_code)

    @mock.patch("db.data.load_low_level")
    def test_ll_no_offset(self, ll):
        ll.return_value = {}
        resp = self.client.get("/api/v1/%s/low-level" % self.uuid)
        self.assertEqual(200, resp.status_code)
        ll.assert_called_with(self.uuid, 0)

    @mock.patch("db.data.load_low_level")
    def test_ll_numerical_offset(self, ll):
        ll.return_value = {}
        resp = self.client.get("/api/v1/%s/low-level?n=3" % self.uuid)
        self.assertEqual(200, resp.status_code)
        ll.assert_called_with(self.uuid, 3)

    @mock.patch("db.data.load_low_level")
    def test_ll_bad_offset(self, ll):
        resp = self.client.get("/api/v1/%s/low-level?n=x" % self.uuid)
        self.assertEqual(400, resp.status_code)

    @mock.patch("db.data.load_low_level")
    def test_ll_no_item(self, ll):
        ll.side_effect = db.exceptions.NoDataFoundException
        resp = self.client.get("/api/v1/%s/low-level" % self.uuid)
        self.assertEqual(404, resp.status_code)
        self.assertEqual("Not found", resp.json["message"])

    @mock.patch("db.data.load_high_level")
    def test_hl_numerical_offset(self, hl):
        hl.return_value = {}
        resp = self.client.get("/api/v1/%s/high-level?n=3" % self.uuid)
        self.assertEqual(200, resp.status_code)
        hl.assert_called_with(self.uuid, 3)

    @mock.patch('db.data.load_low_level')
    def test_get_recordings(self, load_low_level):
        recordings_url = self.test_recording1_mbid + ':0'
        load_low_level.return_value = self.test_recording1_data
        resp = self.client.get('api/v1/recordings?ids=' + recordings_url)
        self.assertEqual(resp.status_code, 200)

        expected_result = {
            self.test_recording1_mbid : {'0': self.test_recording1_data}
            }
        self.assertEqual(resp.json, expected_result)

        recordings_url = recordings_url + ";" + self.test_recording2_mbid
        resp = self.client.get('api/v1/recordings?ids=' + recordings_url)
        self.assertEqual(resp.status_code, 200)

        expected_result = {
            self.test_recording1_mbid : {'0': self.test_recording1_data},
            self.test_recording2_mbid : {'0': self.test_recording1_data}
            }
        self.assertEqual(resp.json, expected_result)

        limit_exceed_url = ";" + self.test_recording1_mbid
        limit_exceed_url = limit_exceed_url * 205
        resp = self.client.get('api/v1/recordings?ids=' + recordings_url + limit_exceed_url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual('More than 200 recordings not allowed per request', resp.json['message'])

        recordings_url = 'something_bad'
        resp = self.client.get('api/v1/recordings?ids=' + recordings_url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual('One or more recording ids invalid', resp.json['message'])

