from __future__ import absolute_import
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import db.exceptions
import mock
import uuid
import os
from webserver.views.api.v1 import core
import json
import webserver
import copy


class CoreViewsTestCase(ServerTestCase):

    def setUp(self):
        super(CoreViewsTestCase, self).setUp()
        self.uuid = str(uuid.uuid4())
        
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

    @mock.patch("webserver.external.messybrainz.get_messybrainz_id")
    def test_submit_low_level_nombid(self, mb):
        md5 = "335679c30222c2b482337ef4570fe758"

        with open(os.path.join(TEST_DATA_PATH, md5 + ".json")) as json_file:
            jsondata = json.load(json_file)

            with self.app.test_client() as client:
                #bad data
                jsonstring = 'bad: data format'
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 400)
                self.assertRaises(webserver.views.api.exceptions.APIBadRequest)
                #recordings id present
                jsondata['metadata']['tags']['musicbrainz_recordingid'] = '1234567890'
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 400)
                #musicbrainz_trackid present
                del jsondata['metadata']['tags']['musicbrainz_recordingid']
                jsondata['metadata']['tags']['musicbrainz_trackid'] = '1234567890'
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 400)
                self.assertRaises(webserver.views.api.exceptions.APIBadRequest)
                #good data
                mb.return_value = '4a069392-d880-4498-b80f-f4c86a1d7dc0', 'msid'
                del jsondata['metadata']['tags']['musicbrainz_trackid']
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 201)
                #test md5 duplicate successfull after data insertion
                resp = client.post("/api/v1/low-level-nombid",
                                    data=jsonstring,
                                    content_type="application/json")
                self.assertEqual(resp.status_code, 200)
                #
                jsondata['metadata']['audio_properties']['md5_encoded'] = '335679c30222c2b482337ef4570fe750'
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 201)
                #test artist and title
                del jsondata['metadata']['tags']['artist']
                jsondata['metadata']['audio_properties']['md5_encoded'] = '335679c30222c2b482337ef4570fe751'
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 400)
                self.assertRaises(webserver.views.api.exceptions.APIBadRequest)
                jsondata['metadata']['tags']['artist'] = 'test artist'
                del jsondata['metadata']['tags']['title']
                jsondata['metadata']['audio_properties']['md5_encoded'] = '335679c30222c2b482337ef4570fe752'
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 400)
                self.assertRaises(webserver.views.api.exceptions.APIBadRequest)
                #additional metadata to messybrainz
                jsondata['metadata']['tags']['title'] = 'test title'
                jsondata['metadata']['audio_properties']['md5_encoded'] = '335679c30222c2b482337ef4570fe753'
                jsondata['metadata']['tags']['track nu'] = 5
                jsondata['metadata']['tags']['album'] = 'test album'
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 201)
                #no mbid nor md5
                del jsondata['metadata']['audio_properties']['md5_encoded']
                jsonstring = json.dumps(jsondata)
                resp = client.post("/api/v1/low-level-nombid",
                                   data=jsonstring,
                                   content_type="application/json")
                self.assertEqual(resp.status_code, 400)
                self.assertRaises(webserver.views.api.exceptions.APIBadRequest)
                #[TODO] (error calling messybrainz)

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
