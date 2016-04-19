from webserver.testing import ServerTestCase
from flask import url_for


class HomeTestCase(ServerTestCase):

    def test_access(self):
        self.assertStatus(self.client.get(url_for('admin.index')), 302)
