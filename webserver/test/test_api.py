from webserver.testing import ServerTestCase
import mock
import uuid
import db.exceptions

class APITestCase(ServerTestCase):

    def setUp(self):
        self.uuid = str(uuid.uuid4())

    @mock.patch("db.data.load_low_level")
    def test_ll_bad_uuid(self, ll):
        resp = self.client.get('/nothing/low-level')
        self.assertEqual(404, resp.status_code)

    @mock.patch("db.data.load_low_level")
    def test_ll_no_offset(self, ll):
        ll.return_value = {}
        resp = self.client.get('/%s/low-level' % self.uuid)
        self.assertEqual(200, resp.status_code)
        ll.assert_called_with(self.uuid, 0)

    @mock.patch("db.data.load_low_level")
    def test_ll_numerical_offset(self, ll):
        ll.return_value = {}
        resp = self.client.get('/%s/low-level?n=3' % self.uuid)
        self.assertEqual(200, resp.status_code)
        ll.assert_called_with(self.uuid, 3)

    @mock.patch("db.data.load_low_level")
    def test_ll_bad_offset(self, ll):
        resp = self.client.get('/%s/low-level?n=x' % self.uuid)
        self.assertEqual(400, resp.status_code)

    @mock.patch("db.data.load_low_level")
    def test_ll_no_item(self, ll):
        ll.side_effect = db.exceptions.NoDataFoundException
        resp = self.client.get('/%s/low-level' % self.uuid)
        self.assertEqual(404, resp.status_code)
        self.assertEqual("Not found", resp.json["message"])

    @mock.patch("db.data.load_high_level")
    def test_hl_numerical_offset(self, hl):
        hl.return_value = {}
        resp = self.client.get('/%s/high-level?n=3' % self.uuid)
        self.assertEqual(200, resp.status_code)
        hl.assert_called_with(self.uuid, 3)
