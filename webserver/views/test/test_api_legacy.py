from __future__ import absolute_import
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import os


class APILegacyViewsTestCase(ServerTestCase):

    def test_get_low_level(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get("/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get("/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 200)

    def test_submit_low_level(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'

        with open(os.path.join(TEST_DATA_PATH, mbid + '.json')) as json_file:
            with self.app.test_client() as client:
                sub_resp = client.post("/%s/low-level" % mbid,
                                       data=json_file.read(),
                                       content_type='application/json')
                self.assertEqual(sub_resp.status_code, 200)

        resp = self.client.get("/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 200)

    def test_cors_headers(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        self.load_low_level_data(mbid)

        resp = self.client.get("/%s/low-level" % mbid)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')

        # TODO: Test in get_high_level.
