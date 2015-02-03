from acousticbrainz.testing import FlaskTestCase
from flask import url_for


class DataViewsTestCase(FlaskTestCase):

    def test_api(self):
        resp = self.client.get(url_for('data.api'))
        self.assertEquals(resp.status_code, 302)  # Should redirect to data page

    def test_data(self):
        resp = self.client.get(url_for('data.data'))
        self.assert200(resp)

    def test_view_low_level(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('data.view_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get(url_for('data.view_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)

    def test_summary(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('data.summary', mbid=mbid))
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get(url_for('data.summary', mbid=mbid))
        self.assertEqual(resp.status_code, 200)
