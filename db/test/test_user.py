# -*- coding: utf-8 -*-
from db.testing import DatabaseTestCase
import db.user
import db.exceptions


class UserTestCase(DatabaseTestCase):

    def test_create(self):
        user_id = db.user.create("fuzzy_dunlop")
        self.assertIsNotNone(db.user.get(user_id))

    def test_create_unicode(self):
        # Testing Unicode
        user_id = db.user.create(u"Пользователь")
        self.assertIsNotNone(user_id)

    def test_get(self):
        user_id = db.user.create("fuzzy_dunlop")
        self.assertIsNotNone(db.user.get(user_id))

        self.assertIsNone(db.user.get(user_id + 2))

    def test_get_by_mb_id(self):
        musicbrainz_id = "fuzzy_dunlop"
        self.assertIsNone(db.user.get_by_mb_id(musicbrainz_id))

        user_id = db.user.create(musicbrainz_id)
        user = db.user.get_by_mb_id(musicbrainz_id)
        self.assertIsNotNone(user)
        self.assertEqual(user["id"], user_id)

    def test_get_by_mb_id_lowercase(self):
        musicbrainz_id = "fuzzy_dunlop"
        self.assertIsNone(db.user.get_by_mb_id(musicbrainz_id))

        user_id = db.user.create("Fuzzy_Dunlop")
        user = db.user.get_by_mb_id(musicbrainz_id)
        self.assertIsNotNone(user)
        self.assertEqual(user["id"], user_id)

    def test_get_or_create(self):
        musicbrainz_id = "User"
        user = db.user.get_or_create(musicbrainz_id)
        self.assertIsNotNone(user)

        same_user = db.user.get_or_create(musicbrainz_id)
        self.assertEqual(user["id"], same_user["id"])

    def test_get_or_create_unicode(self):
        # Testing Unicode
        musicbrainz_id = u"Пользователь"
        user = db.user.get_or_create(musicbrainz_id)
        self.assertIsNotNone(user)

        same_user = db.user.get_or_create(musicbrainz_id)
        self.assertEqual(user["id"], same_user["id"])

    def test_get_admins(self):
        self.assertEqual(len(db.user.get_admins()), 0)
        musicbrainz_id = "fuzzy_dunlop"
        db.user.set_admin(musicbrainz_id, admin=True, force=True)
        admins = db.user.get_admins()
        self.assertEqual(len(db.user.get_admins()), 1)
        self.assertEqual(admins[0]["musicbrainz_id"], musicbrainz_id)

    def test_set_admin(self):
        musicbrainz_id = u"Another Пользователь"
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.user.set_admin(musicbrainz_id, admin=True)

        db.user.set_admin(musicbrainz_id, admin=True, force=True)
        user = db.user.get_by_mb_id(musicbrainz_id)
        self.assertIsNotNone(user)
        self.assertTrue(user["admin"])

        db.user.set_admin(musicbrainz_id, admin=False)
        self.assertFalse(db.user.get_by_mb_id(musicbrainz_id)["admin"])

        user = db.user.get_or_create("fuzzy_dunlop")
        self.assertFalse(user["admin"])
        db.user.set_admin(user["musicbrainz_id"], admin=True, force=True)
        self.assertTrue(db.user.get(user["id"])["admin"])
