from __future__ import absolute_import
from webserver import create_app
from webserver.testing import ServerTestCase
from flask import url_for


class IndexViewsTestCase(ServerTestCase):

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)

    def test_downloads(self):
        resp = self.client.get(url_for('index.downloads'))
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

    def test_flask_debugtoolbar(self):
        """ Test if flask debugtoolbar is loaded correctly

        Creating an app with default config so that debug is True
        and SECRET_KEY is defined.
        """
        app = create_app(debug=True)
        client = app.test_client()
        resp = client.get(url_for('index.goals'))
        self.assert200(resp)
        self.assertIn('flDebug', str(resp.data))
