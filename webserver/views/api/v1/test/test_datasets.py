from __future__ import absolute_import
from werkzeug.exceptions import InternalServerError
from webserver.testing import ServerTestCase
import webserver.views.api
import db.exceptions
import flask
import webserver.views.api.exceptions
import webserver.views.api.v1.datasets
from utils import dataset_validator
from contextlib import contextmanager
import db

import json
import mock
import uuid


class GetCheckDatasetTestCase(ServerTestCase):

    def setUp(self):
        super(GetCheckDatasetTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = db.user.create(self.test_user_mb_name)
        db.user.agree_to_gdpr(self.test_user_mb_name)
        self.test_user = db.user.get(self.test_user_id)

    # In these tests we directly call the view functions instead of accessing
    # them through the webserver with the test client. Because of this we need
    # a temporary application context
    # We have to duplicate the functionality of self.temporary_login, because we
    # need the session data in the app context instead of in the test client context
    @contextmanager
    def context(self):
        with self.create_app().app_context():
            flask.session["user_id"] = self.test_user_id
            flask.session["_fresh"] = True
            yield

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_no_id(self, dataset_get):
        """ Get a dataset if its id doesn't exist """

        dataset_get.side_effect = db.exceptions.NoDataFoundException("Doesn't exist")
        with self.assertRaises(webserver.views.api.exceptions.APINotFound):
            webserver.views.api.v1.datasets.get_check_dataset("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")
        dataset_get.assert_called_once_with("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_public(self, dataset_get):
        # You can access a public dataset
        dataset = {"test": "dataset", "public": True}
        dataset_get.return_value = dataset

        res = webserver.views.api.v1.datasets.get_check_dataset("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")
        self.assertEqual(res, dataset)
        dataset_get.assert_called_once_with("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_private(self, dataset_get):
        """ If a dataset is private, only the owner can retrieve it """

        def get(id):
            return {"id": id, "public": False, "author": self.test_user_id}
        dataset_get.side_effect = get

        with self.context():
            dataset = webserver.views.api.v1.datasets.get_check_dataset("d0d11ad2-df0d-4689-8b71-b041905d7893")
            # OK, we got it
            self.assertDictEqual(dataset, {"id": "d0d11ad2-df0d-4689-8b71-b041905d7893", "public": False, "author": 1})

        # Different owner raises exception
        def get(id):
            return {"id": id, "public": False, "author": self.test_user_id + 1}
        dataset_get.side_effect = get

        with self.context():
            try:
                webserver.views.api.v1.datasets.get_check_dataset("d0d11ad2-df0d-4689-8b71-b041905d7893")
                self.fail("Shouldn't get here")
            except webserver.views.api.exceptions.APINotFound:
                pass

        # Different owner can get a public dataset
        def get(id):
            return {"id": id, "public": True, "author": self.test_user_id + 1}
        dataset_get.side_effect = get
        with self.context():
            dataset = webserver.views.api.v1.datasets.get_check_dataset("d0d11ad2-df0d-4689-8b71-b041905d7893")
            self.assertDictEqual(dataset, {"id": "d0d11ad2-df0d-4689-8b71-b041905d7893", "public": True, "author": 2})

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_write(self, dataset_get):
        """ If we want write access, it must be owned by the current user """

        # not owned by current user but we want to write
        def get(id):
            return {"id": id, "public": True, "author": self.test_user_id + 1}
        dataset_get.side_effect = get

        with self.context():
            try:
                webserver.views.api.v1.datasets.get_check_dataset("d0d11ad2-df0d-4689-8b71-b041905d7893", write=True)
                self.fail("Shouldn't get here")
            except webserver.views.api.exceptions.APIUnauthorized as e:
                self.assertEqual(e.message, "Only the author can modify the dataset.")

        # owned by current user + write
        def get(id):
            return {"id": id, "public": True, "author": self.test_user_id}
        dataset_get.side_effect = get
        with self.context():
            dataset = webserver.views.api.v1.datasets.get_check_dataset("d0d11ad2-df0d-4689-8b71-b041905d7893", write=True)
            self.assertDictEqual(dataset, {"id": "d0d11ad2-df0d-4689-8b71-b041905d7893", "public": True, "author": 1})


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
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json")
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
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json")
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
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "dataset_id": "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.update_dataset_meta")
    @mock.patch("db.dataset.get")
    def test_update_dataset_details(self, dataset_get, update_dataset_meta):
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {"name": "new name"}

        url = "/api/v1/datasets/%s" % (str(dsid))
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        update_dataset_meta.assert_called_with(dsid, submit)

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Dataset updated."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_update_dataset_details_invalid(self, dataset_get):
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {"invalidfield": "data"}

        url = "/api/v1/datasets/%s" % (str(dsid))
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Unexpected field `invalidfield` in dataset dictionary."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_update_dataset_details_no_dataset(self, dataset_get):
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"

        dataset_get.side_effect = db.exceptions.NoDataFoundException("Doesn't exist")

        submit = {}
        url = "/api/v1/datasets/%s" % (str(dsid))
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        self.assertEqual(resp.status_code, 404)
        expected = {"message": "Can't find this dataset."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_update_dataset_details_bad_uuid(self, dataset_get):
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240xxxx"

        dataset_get.side_effect = {}
        submit = {}
        url = "/api/v1/datasets/%s" % (dsid)
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        self.assertEqual(resp.status_code, 404)
        expected_result = {"message": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."}
        self.assertEqual(resp.json, expected_result)

    @mock.patch("db.dataset.get")
    def test_update_dataset_details_unknown_error(self, dataset_get):
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"

        dataset_get.side_effect = InternalServerError()
        submit = {}
        url = "/api/v1/datasets/%s" % (dsid)
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        self.assertEqual(resp.status_code, 500)
        expected_result = {"message": "An unknown error occurred"}
        self.assertEqual(resp.json, expected_result)

    @mock.patch("db.dataset.add_class")
    @mock.patch("db.dataset.get")
    def test_add_class(self, dataset_get, add_class):
        """Add a class"""
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "name": "Class #2",
            "description": "This is class number 2",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6",]
        }
        url = "/api/v1/datasets/%s/classes" % (str(dsid))
        resp = self.client.post(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        add_class.assert_called_with(dsid, submit)

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class added."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_add_class_invalid_data(self, dataset_get):
        """ An invalid submission results in HTTP 400 """
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        # We test if the dataset is valid before the submitted data
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}
        submit = {
            "name": "Class #2",
            "invalid": "data"
        }
        url = "/api/v1/datasets/%s/classes" % (str(dsid))
        resp = self.client.post(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Unexpected field `invalid` in class."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.add_class")
    @mock.patch("db.dataset.get")
    def test_add_class_unique_recordings(self, dataset_get, add_class):
        """ If a UUID is duplicated in the recordings list, remove it before passing
            to `add_class` """
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "name": "Class #2",
            "description": "This is class number 2",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6", "323565da-57b1-4eae-b3c4-cdf431061391", "1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        url = "/api/v1/datasets/%s/classes" % (str(dsid))
        resp = self.client.post(url, data=json.dumps(submit), content_type="application/json")

        expected = {
            "name": "Class #2",
            "description": "This is class number 2",
            "recordings": ["323565da-57b1-4eae-b3c4-cdf431061391", "1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        add_class.assert_called_with(dsid, expected)
        dataset_get.assert_called_with(uuid.UUID(dsid))

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class added."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.delete_class")
    @mock.patch("db.dataset.get")
    def test_delete_class(self, dataset_get, delete_class):
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {"name": "rock"}
        url = "/api/v1/datasets/%s/classes" % (str(dsid))
        resp = self.client.delete(url, data=json.dumps(submit), content_type="application/json")
        delete_class.assert_called_with(dsid, submit)
        dataset_get.assert_called_with(uuid.UUID(dsid))

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class deleted."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.delete_class")
    @mock.patch("db.dataset.get")
    def test_delete_class_invalid_data(self, dataset_get, delete_class):
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        # We test if the dataset is valid before the submitted data
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {"invalid": "data"}
        url = "/api/v1/datasets/%s/classes" % (str(dsid))
        resp = self.client.delete(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        delete_class.assert_not_called()
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Field `name` is missing from class."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.update_class")
    @mock.patch("db.dataset.get")
    def test_update_class(self, dataset_get, update_class):
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "name": "Class #1",
            "new_name": "new class"
        }
        url = "/api/v1/datasets/%s/classes" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        update_class.assert_called_with(dsid, "Class #1", submit)

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Class updated."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.update_class")
    @mock.patch("db.dataset.get")
    def test_update_class_bad_data(self, dataset_get, update_class):
        """ Test that we get http 400 if the data is invalid"""
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "new_name": "new class"
        }
        url = "/api/v1/datasets/%s/classes" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        update_class.assert_not_called()

        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Field `name` is missing from class."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.update_class")
    @mock.patch("db.dataset.get")
    def test_update_class_no_class(self, dataset_get, update_class):
        """ Test that we get http 400 if the class name doesn't exist"""
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}
        update_class.side_effect = db.exceptions.NoDataFoundException("No such class exists.")

        submit = {
            "name": "Class #999",
            "new_name": "new class"
        }
        url = "/api/v1/datasets/%s/classes" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        update_class.assert_called_with(dsid, "Class #999", submit)

        self.assertEqual(resp.status_code, 400)
        expected = {"message": "No such class exists."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.add_recordings")
    @mock.patch("db.dataset.get")
    def test_add_recordings(self, dataset_get, add_recordings):
        """Successfully add recordings. """
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        add_recordings.assert_called_with(dsid, "Class #1", ["1c085555-3805-428a-982f-e14e0a2b18e6"])

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recordings added."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.add_recordings")
    @mock.patch("db.dataset.get")
    def test_add_recordings_unique_recordings(self, dataset_get, add_recordings):
        """ If a UUID is duplicated in the recordings list, remove it before passing
            to `add_recordings` """
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "class_name": "Class #1",
            "recordings": ["ed94c67d-bea8-4741-a3a6-593f20a22eb6", "1c085555-3805-428a-982f-e14e0a2b18e6",
                           "ed94c67d-bea8-4741-a3a6-593f20a22eb6"]
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        add_recordings.assert_called_with(dsid, "Class #1", ["ed94c67d-bea8-4741-a3a6-593f20a22eb6",
                                                             "1c085555-3805-428a-982f-e14e0a2b18e6"])

        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "message": "Recordings added."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_add_recordings_invalid_data(self, dataset_get):
        """ Invalid data results in a 400 and query is not made """

        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        # We test if the dataset is valid before the submitted data
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "class_name": "Class #1",
            "invalid": "field"
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Field `recordings` is missing from recordings dictionary."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.add_recordings")
    @mock.patch("db.dataset.get")
    def test_add_recordings_no_such_class(self, dataset_get, add_recordings):
        """ Try and add recordings to a dataset which exists, but no class with this name exists """
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        # We test if the dataset is valid before the submitted data
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        add_recordings.side_effect = db.exceptions.NoDataFoundException("No such class exists.")

        submit = {
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.put(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "No such class exists."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.delete_recordings")
    @mock.patch("db.dataset.get")
    def test_delete_recordings(self, dataset_get, delete_recordings):
        """Successfully delete recordings. """
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "class_name": "Class #2",
            "recordings": ["ed94c67d-bea8-4741-a3a6-593f20a22eb6", "19e698e7-71df-48a9-930e-d4b1a2026c82"]
        }

        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.delete(url, data=json.dumps(submit), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        delete_recordings.assert_called_with(dsid, "Class #2", ["19e698e7-71df-48a9-930e-d4b1a2026c82",
                                                                "ed94c67d-bea8-4741-a3a6-593f20a22eb6"])
        dataset_get.assert_called_with(uuid.UUID(dsid))
        expected = {"success": True, "message": "Recordings deleted."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.delete_recordings")
    @mock.patch("db.dataset.get")
    def test_delete_recordings_unique_recordings(self, dataset_get, delete_recordings):
        """ If a UUID is duplicated in the recordings list, remove it before passing
            to `add_recordings` """
        self.temporary_login(self.test_user_id)

        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "class_name": "Class #1",
            "recordings": ["ed94c67d-bea8-4741-a3a6-593f20a22eb6", "1c085555-3805-428a-982f-e14e0a2b18e6",
                           "ed94c67d-bea8-4741-a3a6-593f20a22eb6"]
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.delete(url, data=json.dumps(submit), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        dataset_get.assert_called_with(uuid.UUID(dsid))
        delete_recordings.assert_called_with(dsid, "Class #1", ["ed94c67d-bea8-4741-a3a6-593f20a22eb6",
                                                             "1c085555-3805-428a-982f-e14e0a2b18e6"])

        expected = {"success": True, "message": "Recordings deleted."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_delete_recordings_invalid_data(self, dataset_get):
        """ Invalid data results in a 400 and query is not made """

        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        # We test if the dataset is valid before the submitted data
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        submit = {
            "class_name": "Class #1",
            "invalid": "field"
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.delete(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Field `recordings` is missing from recordings dictionary."}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.delete_recordings")
    @mock.patch("db.dataset.get")
    def test_delete_recordings_no_such_class(self, dataset_get, delete_recordings):
        """ Try and add recordings to a dataset which exists, but no class with this name exists """
        self.temporary_login(self.test_user_id)
        dsid = "e01f7638-3902-4bd4-afda-ac73d240a4b3"
        # We test if the dataset is valid before the submitted data
        dataset_get.return_value = {"id": dsid, "author": self.test_user_id, "public": False}

        delete_recordings.side_effect = db.exceptions.NoDataFoundException("No such class exists.")

        submit = {
            "class_name": "Class #1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        url = "/api/v1/datasets/%s/recordings" % dsid
        resp = self.client.delete(url, data=json.dumps(submit), content_type="application/json")

        dataset_get.assert_called_with(uuid.UUID(dsid))
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "No such class exists."}
        self.assertEqual(resp.json, expected)

