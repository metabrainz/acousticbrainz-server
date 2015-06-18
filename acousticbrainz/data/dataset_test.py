from acousticbrainz.testing import ServerTestCase
from acousticbrainz.data import dataset, user


class DatasetTestCase(ServerTestCase):

    def setUp(self):
        super(DatasetTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = user.create(self.test_user_mb_name)

        self.test_data = {
            "name": "Test",
            "description": "",
            "classes": [],
            "public": True,
        }

    def test_create_from_dict(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        self.assertIsNotNone(dataset.get(id))
