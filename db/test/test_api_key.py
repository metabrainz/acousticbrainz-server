from db.testing import DatabaseTestCase
import db.exceptions
import db.api_key
import db.user
import six


class APIKeyTestCase(DatabaseTestCase):

    def setUp(self):
        super(APIKeyTestCase, self).setUp()
        self.user_id = db.user.create("fuzzy_dunlop")

    def test_generate(self):
        key = db.api_key.generate(self.user_id)
        self.assertIsNotNone(key)
        self.assertEqual(len(key), 40)
        self.assertIsInstance(key, six.string_types)

    def test_get_active(self):
        keys = db.api_key.get_active(self.user_id)
        self.assertEqual(len(keys), 0)

        key_1 = db.api_key.generate(self.user_id)
        keys = db.api_key.get_active(self.user_id)
        self.assertEqual(len(keys), 1)
        self.assertIn(key_1, keys)

        key_2 = db.api_key.generate(self.user_id)
        keys = db.api_key.get_active(self.user_id)
        self.assertEqual(len(keys), 2)
        self.assertIn(key_2, keys)
        self.assertIn(key_1, keys)

    def test_revoke(self):
        key = db.api_key.generate(self.user_id)
        self.assertTrue(db.api_key.is_active(key))
        db.api_key.revoke(key)
        self.assertFalse(db.api_key.is_active(key))

    def test_revoke_all(self):
        key_1 = db.api_key.generate(self.user_id)
        key_2 = db.api_key.generate(self.user_id)
        self.assertTrue(db.api_key.is_active(key_1))
        self.assertTrue(db.api_key.is_active(key_2))

        db.api_key.revoke_all(self.user_id)
        self.assertFalse(db.api_key.is_active(key_1))
        self.assertFalse(db.api_key.is_active(key_2))

    def test_is_active(self):
        key = db.api_key.generate(self.user_id)
        self.assertTrue(db.api_key.is_active(key))

        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.api_key.is_active("fakeKey42")
