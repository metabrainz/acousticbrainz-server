from webserver.testing import ServerTestCase
from flask import url_for


class AdminsTestCase(ServerTestCase):

    def test_access(self):
        self.assertStatus(self.client.get(url_for('adminsview.index')), 302)
