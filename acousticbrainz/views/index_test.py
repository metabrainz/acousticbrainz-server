from acousticbrainz.testing import FlaskTestCase
from flask import url_for


class IndexViewsTestCase(FlaskTestCase):

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)

    def test_download(self):
        resp = self.client.get(url_for('index.download'))
        self.assert200(resp)

    def test_contribute(self):
        resp = self.client.get(url_for('index.contribute'))
        self.assert200(resp)

    def test_goals(self):
        resp = self.client.get(url_for('index.goals'))
        self.assert200(resp)

    def test_faq(self):
        resp = self.client.get(url_for('index.faq'))
        self.assert200(resp)
