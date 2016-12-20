from __future__ import absolute_import
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import db.exceptions
from utils import dataset_validator

import json
import mock
import os
import uuid


class APIDatasetViewsTestCase(ServerTestCase):

    def setUp(self):
        super(APIDatasetViewsTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = db.user.create(self.test_user_mb_name)
        self.test_user = db.user.get(self.test_user_id)


    def test_create_dataset_forbidden(self):
        """ Not logged in. """
        resp = self.client.post("/api/v1/datasets/")
        self.assertEqual(resp.status_code, 401)


    def test_create_dataset_no_data(self):
        """ No data or bad data POSTed. """
        self.temporary_login(self.test_user_id)

        resp = self.client.post("/api/v1/datasets/")
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Data must be submitted in JSON format."}
        self.assertEqual(resp.json, expected)

        resp = self.client.post("/api/v1/datasets/", data="test-not-json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json, expected)


    @mock.patch("db.dataset.create_from_dict")
    def test_create_dataset_validation_error(self, create_from_dict):
        """ return an error if create_from_dict returns a validation error """
        self.temporary_login(self.test_user_id)

        exception_error = "data is not valid"
        create_from_dict.side_effect = dataset_validator.ValidationException(exception_error)
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        expected = {"message": exception_error}
        self.assertEqual(resp.json, expected)


    @mock.patch("db.dataset.create_from_dict")
    def test_create_dataset_fields_added(self, create_from_dict):
        """ Fields are added to the dict before validation if they don't exist. """
        self.temporary_login(self.test_user_id)

        exception_error = "data is not valid"
        create_from_dict.side_effect = dataset_validator.ValidationException(exception_error)
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        # The `public` and `classes` fields are added
        create_from_dict.assert_called_once_with({"a": "thing", "public": True, "classes": []}, self.test_user["id"])


    @mock.patch("db.dataset.create_from_dict")
    def test_create_dataset(self, create_from_dict):
        """ Successfully creates dataset. """
        self.temporary_login(self.test_user_id)
        create_from_dict.return_value = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        # Json format doesn't matter as we mock the create response
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "dataset_id": "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"}
        self.assertEqual(resp.json, expected)


    def test_add_recordings(self):
        """Successfully add recordings. """
        self.temporary_login(self.test_user_id)
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6",]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.put(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recording(s) added."}
        self.assertEqual(resp.json, expected)


    def test_delete_recordings(self):
        """Successfully delete recordings. """
        self.temporary_login(self.test_user_id)
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "class_name": "Class #2",
            "recordings": ["ed94c67d-bea8-4741-a3a6-593f20a22eb6","19e698e7-71df-48a9-930e-d4b1a2026c82",]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recording(s) deleted."}
        self.assertEqual(resp.json, expected)


    def test_add_invalid_recordings_(self):
        """Test for adding invalid UUID format recordings. """
        self.temporary_login(self.test_user_id)
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-not-a-uuid", ]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.put(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "MBID 1c085555-3805-428a-not-a-uuid not a valid UUID"}
        self.assertEqual(resp.json, expected)


    def test_delete_invalid_recordings(self):
        """Test for deleting invalid UUID format recordings. """
        self.temporary_login(self.test_user_id)
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "class_name": "Class #2",
            "recordings": ["ed94c67d-bea8-4741-a3a6-593f20a22eb6", "19e698e7-71df-48a9-930e-invalidUUID", ]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "MBID 19e698e7-71df-48a9-930e-invalidUUID not a valid UUID"}
        self.assertEqual(resp.json, expected)


    def test_add_duplicate_recordings(self):
        """Test for adding duplicate recordings. """
        self.temporary_login(self.test_user_id)
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6", "1c085555-3805-428a-982f-e14e0a2b18e6",]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.put(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recording(s) added."}
        self.assertEqual(resp.json, expected)


    def test_delete_duplicate_recordings(self):
        """Test for deleting duplicate recordings """
        self.temporary_login(self.test_user_id)
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "class_name": "Class #2",
            "recordings": [
                "ed94c67d-bea8-4741-a3a6-593f20a22eb6",
                "19e698e7-71df-48a9-930e-d4b1a2026c82",
                "19e698e7-71df-48a9-930e-d4b1a2026c82"
            ]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recording(s) deleted."}
        self.assertEqual(resp.json, expected)


    def test_add_recordings_check_for_other_datasets(self):
        """Check the recordings are not added to another dataset"""
        self.temporary_login(self.test_user_id)
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
        self.test_data_another_dataset = {
            "name": "Test2",
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        id2 = db.dataset.create_from_dict(self.test_data_another_dataset, author_id=self.test_user_id)
        original_dataset2 = db.dataset.get(id2)
        submit = json.dumps({
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6",]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.put(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recording(s) added."}
        self.assertEqual(resp.json, expected)
        updated_dataset2 = db.dataset.get(id2)
        self.assertDictEqual(original_dataset2, updated_dataset2)


    def test_delete_recordings_check_for_other_datasets(self):
        """Check the recordings are not deleted from another dataset """
        self.temporary_login(self.test_user_id)
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
        self.test_data_another_dataset = {
            "name": "Test2",
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
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        id2 = db.dataset.create_from_dict(self.test_data_another_dataset, author_id=self.test_user_id)
        original_dataset2 = db.dataset.get(id2)
        submit = json.dumps({
            "class_name": "Class #2",
            "recordings": ["ed94c67d-bea8-4741-a3a6-593f20a22eb6","19e698e7-71df-48a9-930e-d4b1a2026c82",]
        })
        url = '/api/v1/datasets/%s/recordings' % (str(id))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recording(s) deleted."}
        self.assertEqual(resp.json, expected)
        updated_dataset2 = db.dataset.get(id2)
        self.assertDictEqual(original_dataset2, updated_dataset2)


    def test_add_class(self):
        """Add a class successfully"""
        self.temporary_login(self.test_user_id)
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
            ],
            "public": True,
        }
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "name": "Class #2",
            "description": "This is class number 2",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6",]
        })
        url = '/api/v1/datasets/%s/classes' % (str(id))
        resp = self.client.post(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class added."}
        self.assertEqual(resp.json, expected)


    def test_delete_class(self):
        """Delete a class successfully"""
        self.temporary_login(self.test_user_id)
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
            ],
            "public": True,
        }
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "name": "Class #1",
        })
        url = '/api/v1/datasets/%s/classes' % (str(id))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class deleted."}
        self.assertEqual(resp.json, expected)


    def test_add_class_without_recordings(self):
        """Add a class without recordings and description successfully"""
        self.temporary_login(self.test_user_id)
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
                    ],
                },
            ],
            "public": True,
        }
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "name": "Class #2",
        })
        url = '/api/v1/datasets/%s/classes' % (str(id))
        resp = self.client.post(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class added."}
        self.assertEqual(resp.json, expected)


    def test_add_class_already_present(self):
        self.temporary_login(self.test_user_id)
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
            ],
            "public": True,
        }
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "name": "Class #1",
        })
        url = '/api/v1/datasets/%s/classes' % (str(id))
        resp = self.client.post(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)


    def test_add_class_check_other_dataset(self):
        """Check another dataset after adding class to a dataset"""
        self.temporary_login(self.test_user_id)
        self.test_data = {
            "name": "Test1",
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
            ],
            "public": True,
        }
        self.test_data_another_dataset = {
            "name": "Test2",
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
            ],
            "public": True,
        }
        id1 = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        id2 = db.dataset.create_from_dict(self.test_data_another_dataset, author_id=self.test_user_id)
        original = db.dataset.get(id2)
        submit = json.dumps({
            "name": "Class #2",
        })
        url = '/api/v1/datasets/%s/classes' % (str(id1))
        resp = self.client.post(url, data=submit, content_type='application/json')
        updated = db.dataset.get(id2)
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class added."}
        self.assertEqual(resp.json, expected)
        self.assertDictEqual(original, updated)


    def test_add_class_with_wrong_recordings(self):
        """Add a class with recordings in wrong UUID format"""
        self.temporary_login(self.test_user_id)
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
            ],
            "public": True,
        }
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "name": "Class #2",
            "description": "This is class number 2",
            "recordings": ["1c085555-3805-428a-982f-wrong-UUID", ]
        })
        url = '/api/v1/datasets/%s/classes' % (str(id))
        resp = self.client.post(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "MBID 1c085555-3805-428a-982f-wrong-UUID not a valid UUID"}
        self.assertEqual(resp.json, expected)


    def test_delete_class_not_present(self):
        """Delete a class not present in the dataset"""
        self.temporary_login(self.test_user_id)
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
            ],
            "public": True,
        }
        id = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        submit = json.dumps({
            "name": "Class #2",
        })
        url = '/api/v1/datasets/%s/classes' % (str(id))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Class does not exists."}
        self.assertEqual(resp.json, expected)


    def test_delete_class_check_other_dataset(self):
        """Check another dataset after deleted class from a dataset"""
        self.temporary_login(self.test_user_id)
        self.test_data = {
            "name": "Test1",
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
            ],
            "public": True,
        }
        self.test_data_another_dataset = {
            "name": "Test2",
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
            ],
            "public": True,
        }
        id1 = db.dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        id2 = db.dataset.create_from_dict(self.test_data_another_dataset, author_id=self.test_user_id)
        original = db.dataset.get(id2)
        submit = json.dumps({
            "name": "Class #1",
        })
        url = '/api/v1/datasets/%s/classes' % (str(id1))
        resp = self.client.delete(url, data=submit, content_type='application/json')
        updated = db.dataset.get(id2)
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class deleted."}
        self.assertEqual(resp.json, expected)
        self.assertDictEqual(original, updated)