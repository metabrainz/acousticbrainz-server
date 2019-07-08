from webserver.testing import ServerTestCase
from flask import url_for


class AdminViewsTestCase(ServerTestCase):

    def test_access(self):
        # should redirect to login page
        r = self.client.get(url_for('admin.index'))
        print(r.data)
        self.assertStatus(self.client.get(url_for('admin.index')), 302)
        self.assertStatus(self.client.get(url_for('adminsview.index')), 302)
