from webserver.testing import AcousticbrainzTestCase
from flask import url_for


class HomeTestCase(AcousticbrainzTestCase):

    def test_access(self):
        self.assertStatus(self.client.get(url_for('admin.index')), 302)
