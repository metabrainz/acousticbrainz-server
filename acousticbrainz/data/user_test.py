from acousticbrainz.testing import FlaskTestCase
from acousticbrainz.data import user as user_data


class UserTestCase(FlaskTestCase):

    def test_create(self):
        musicbrainz_id = "fuzzy_dunlop"
        user_id = user_data.create(musicbrainz_id)

        self.assertIsNotNone(user_data.get(user_id))

    def test_get(self):
        user_id = user_data.create("fuzzy_dunlop")
        self.assertIsNotNone(user_data.get(user_id))

        self.assertIsNone(user_data.get(user_id + 2))

    def test_get_by_mb_id(self):
        self.assertIsNone(user_data.get_by_mb_id("fuzzy"))

        musicbrainz_id = "fuzzy_dunlop"
        user_id = user_data.create(musicbrainz_id)
        user = user_data.get_by_mb_id(musicbrainz_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, user_id)

    def test_get_or_create(self):
        self.assertIsNotNone(user_data.get_or_create("fuzzy_dunlop"))
