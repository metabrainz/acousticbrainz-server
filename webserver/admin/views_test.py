from webserver.testing import AcousticbrainzTestCase
from flask import url_for


class AdminViewsTestCase(AcousticbrainzTestCase):

    def test_access(self):
        self.assertStatus(self.client.get(url_for('admin.index')), 302)
        self.assertStatus(self.client.get(url_for('adminsview.index')), 302)
