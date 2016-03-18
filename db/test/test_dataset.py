import db
from db.testing import DatabaseTestCase
from db import dataset, user
import jsonschema
import copy

class DatasetTestCase(DatabaseTestCase):

    def setUp(self):
        super(DatasetTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = user.create(self.test_user_mb_name)

        self.test_data = {
            "name": "Test",
            "description": "",
            "classes": [
                {
                    "name": "Class #1",
                    "description": "This is a description of class #1!",
                    "recordings": [
                        "0dad432b-16cc-4bf0-8961-fd31d124b01b",
                        "19e698e7-71df-48a9-930e-d4b1a2026c82",
                    ]
                },
                {
                    "name": "Class #2",
                    "description": "",
                    "recordings": [
                        "fd528ddb-411c-47bc-a383-1f8a222ed213",
                        "96888f9e-c268-4db2-bc13-e29f8b317c20",
                        "ed94c67d-bea8-4741-a3a6-593f20a22eb6",
                    ]
                },
            ],
            "public": True,
        }

    def test_create_from_dict(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        ds = dataset.get(id)
        self.assertIsNotNone(ds)
        self.assertEqual(len(ds["classes"][0]["recordings"]), 2)
        self.assertEqual(len(ds["classes"][1]["recordings"]), 3)

    def test_create_from_dict_duplicates(self):
        bad_dict = copy.deepcopy(self.test_data)
        bad_dict["classes"][0]["recordings"] = [
            "0dad432b-16cc-4bf0-8961-fd31d124b01b",
            "19e698e7-71df-48a9-930e-d4b1a2026c82",
            "19e698e7-71df-48a9-930e-d4b1a2026c82",
        ]
        id = dataset.create_from_dict(bad_dict, author_id=self.test_user_id)

        ds = dataset.get(id)
        self.assertEqual(len(ds["classes"][0]["recordings"]), 2)
        self.assertIn("19e698e7-71df-48a9-930e-d4b1a2026c82", ds["classes"][0]["recordings"])


    def test_create_from_dict_malformed(self):
        bad_dict = copy.deepcopy(self.test_data)

        bad_dict["classes"][0]["name"] = None
        self.assertRaises(jsonschema.ValidationError, dataset.create_from_dict,
                          dictionary=bad_dict, author_id=self.test_user_id)

        bad_dict["classes"][0]["name"] = ""
        self.assertRaises(jsonschema.ValidationError, dataset.create_from_dict,
                          dictionary=bad_dict, author_id=self.test_user_id)

    def test_update(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        updated_dict = copy.deepcopy(self.test_data)
        updated_dict["classes"][0]["recordings"] = []  # Removing recordings from first class
        dataset.update(
            dataset_id=id,
            dictionary=updated_dict,
            author_id=self.test_user_id,
        )

        ds = dataset.get(id)
        # First class shouldn't have any recordings
        self.assertEqual(len(ds["classes"][0]["recordings"]), 0)
        self.assertEqual(len(ds["classes"][1]["recordings"]), 3)

    def test_update_malformed(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        bad_dataset = copy.deepcopy(self.test_data)

        bad_dataset["classes"][0]["name"] = None
        self.assertRaises(jsonschema.ValidationError, dataset.update,
                          dataset_id=id, dictionary=bad_dataset, author_id=self.test_user_id)

        bad_dataset["classes"][0]["name"] = ""
        self.assertRaises(jsonschema.ValidationError, dataset.update,
                          dataset_id=id, dictionary=bad_dataset, author_id=self.test_user_id)

    def test_get_by_user_id(self):
        dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        datasets = dataset.get_by_user_id(self.test_user_id)
        self.assertEqual(len(datasets), 1)

        private = copy.deepcopy(self.test_data)
        private["name"] = "Private Dataset"
        private["public"] = False
        dataset.create_from_dict(private, author_id=self.test_user_id)

        datasets = dataset.get_by_user_id(self.test_user_id)
        # Not returning private datasets by default.
        self.assertEqual(len(datasets), 1)
        self.assertNotEqual(datasets[0]["name"], private["name"])

        datasets = dataset.get_by_user_id(self.test_user_id, public_only=False)
        self.assertEqual(len(datasets), 2)

    def test_delete(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        self.assertIsNotNone(dataset.get(id))

        dataset.delete(id)
        self.assertIsNone(dataset.get(id))

    def test_last_edited(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        ds = dataset.get(id)
        self.assertEqual(ds['created'], ds['last_edited'])
        with db.engine.begin() as connection:
            connection.execute("""UPDATE dataset SET last_edited = now() - interval %s where id = %s""",
                    ('1 hour', id))
        ds = dataset.get(id)
        self.assertTrue(ds['created'] > ds['last_edited'])
        dataset.update(id, self.test_data, author_id=self.test_user_id)
        ds_updated = dataset.get(id)
        self.assertTrue(ds_updated['last_edited'] > ds['last_edited'])
