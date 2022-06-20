from __future__ import absolute_import
import db
import db.exceptions
from webserver.testing import AcousticbrainzTestCase
from db import dataset, user
from utils import dataset_validator
from sqlalchemy import text
import uuid
import copy
from unittest import mock


class DatasetTestCase(AcousticbrainzTestCase):

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

    def test_create_from_dict_none_description(self):
        bad_dict = copy.deepcopy(self.test_data)
        bad_dict["description"] = None
        bad_dict["classes"][1]["description"] = None
        id = dataset.create_from_dict(bad_dict, author_id=self.test_user_id)
        ds = dataset.get(id)
        self.assertEqual(ds["classes"][1]["description"], "")
        self.assertEqual(ds["description"], "")

    def test_create_from_dict_absence_description(self):
        bad_dict = copy.deepcopy(self.test_data)
        bad_dict.pop("description")
        bad_dict["classes"][1].pop("description")
        id = dataset.create_from_dict(bad_dict, author_id=self.test_user_id)
        ds = dataset.get(id)
        self.assertEqual(ds["classes"][1]["description"], "")
        self.assertEqual(ds["description"], "")

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
        with self.assertRaises(dataset_validator.ValidationException):
            dataset.create_from_dict(bad_dict, author_id=self.test_user_id)

        bad_dict["classes"][0]["name"] = ""
        with self.assertRaises(dataset_validator.ValidationException):
            dataset.create_from_dict(bad_dict, author_id=self.test_user_id)

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
        with self.assertRaises(dataset_validator.ValidationException):
            dataset.update(dataset_id=id, dictionary=bad_dataset, author_id=self.test_user_id)

        bad_dataset["classes"][0]["name"] = ""
        with self.assertRaises(dataset_validator.ValidationException):
            dataset.update(dataset_id=id, dictionary=bad_dataset, author_id=self.test_user_id)

    def test_update_metadata(self):
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        existing_dataset = dataset.get(dsid)
        dataset.update_dataset_meta(dsid, {"name": "new name", "description": "new desc", "public": False})
        new_dataset = dataset.get(dsid)

        self.assertNotEqual(existing_dataset["name"], new_dataset["name"])
        self.assertEqual(new_dataset["name"], "new name")
        self.assertNotEqual(existing_dataset["description"], new_dataset["description"])
        self.assertEqual(new_dataset["description"], "new desc")
        self.assertNotEqual(existing_dataset["public"], new_dataset["public"])
        self.assertEqual(new_dataset["public"], False)

    def test_update_dataset_meta_badmeta(self):
        dsid = str(uuid.uuid4())
        try:
            dataset.update_dataset_meta(dsid, {"name": "new name", "badkey": "badvalue"})
            self.fail("Shouldn't get here")
        except ValueError as e:
            self.assertEqual(str(e), "Unexpected meta value(s): badkey")

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
        with self.assertRaises(db.exceptions.NoDataFoundException):
            dataset.get(id)

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

    def test_create_snapshot(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        snapshots = dataset.get_snapshots_for_dataset(id)
        self.assertEqual(len(snapshots), 0)

        snap_id = dataset.create_snapshot(id)
        snapshots = dataset.get_snapshots_for_dataset(id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["id"], snap_id)

        snap = dataset.get_snapshot(snap_id)
        dataset_snap = copy.deepcopy(self.test_data)
        del dataset_snap["public"]
        self.assertDictEqual(snap["data"], dataset_snap)

    def test_delete_shapshot(self):
        id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        snap_id = dataset.create_snapshot(id)
        snapshots = dataset.get_snapshots_for_dataset(id)
        self.assertEqual(len(snapshots), 1)

        with db.engine.connect() as connection:
            dataset._delete_snapshots_for_dataset(connection, id)
        snapshots = dataset.get_snapshots_for_dataset(id)
        self.assertEqual(len(snapshots), 0)

        with self.assertRaises(db.exceptions.NoDataFoundException):
            dataset.get_snapshot(snap_id)

    def test_add_recordings(self):
        """ Add recordings to an existing class """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        originaldataset = dataset.get(dsid)

        class_name = "Class #1",
        recordings = ["1c085555-3805-428a-982f-e14e0a2b18e6"]
        dataset.add_recordings(dsid, class_name, recordings)

        updateddataset = dataset.get(dsid)

        # Class 1 has been updated with the new recording id
        self.assertEqual(2, len(originaldataset["classes"][0]["recordings"]))
        expected_recordings = ["0dad432b-16cc-4bf0-8961-fd31d124b01b",
                               "19e698e7-71df-48a9-930e-d4b1a2026c82",
                               "1c085555-3805-428a-982f-e14e0a2b18e6"]
        self.assertEqual(set(expected_recordings), set(updateddataset["classes"][0]["recordings"]))

        # Class #2 stays the same as `test_data`
        expected_recordings = ["fd528ddb-411c-47bc-a383-1f8a222ed213",
                               "96888f9e-c268-4db2-bc13-e29f8b317c20",
                               "ed94c67d-bea8-4741-a3a6-593f20a22eb6"]
        self.assertEqual(set(expected_recordings), set(updateddataset["classes"][1]["recordings"]))

    def test_add_recordings_duplicate(self):
        """ A recording id which already exists is skipped """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        class_name = "Class #1",
        recordings = ["0dad432b-16cc-4bf0-8961-fd31d124b01b", "1c085555-3805-428a-982f-e14e0a2b18e6"]
        dataset.add_recordings(dsid, class_name, recordings)

        updateddataset = dataset.get(dsid)
        expected_recordings = ["0dad432b-16cc-4bf0-8961-fd31d124b01b",
                               "19e698e7-71df-48a9-930e-d4b1a2026c82",
                               "1c085555-3805-428a-982f-e14e0a2b18e6"]
        self.assertEqual(set(expected_recordings), set(updateddataset["classes"][0]["recordings"]))

    def test_delete_recordings(self):
        """ Delete recordings from a class """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        originaldataset = dataset.get(dsid)

        class_name = "Class #1",
        recordings = ["19e698e7-71df-48a9-930e-d4b1a2026c82"]

        dataset.delete_recordings(dsid, class_name, recordings)
        updateddataset = dataset.get(dsid)

        # Original dataset has the 2 recordings in Class #1, but the updated one only has 1 remaining
        self.assertEqual(2, len(originaldataset["classes"][0]["recordings"]))
        expected_recordings = ["0dad432b-16cc-4bf0-8961-fd31d124b01b"]
        self.assertEqual(set(expected_recordings), set(updateddataset["classes"][0]["recordings"]))

    def test_delete_recordings_other_class(self):
        """ If there are two datasets with the same class names, the correct one is deleted. """
        ds1id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        ds2id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        class_name = "Class #1",
        recordings = ["19e698e7-71df-48a9-930e-d4b1a2026c82"]
        dataset.delete_recordings(ds2id, class_name, recordings)

        # Dataset 1 has both initial recordings, but it's been removed from dataset 2
        ds1 = dataset.get(ds1id)
        ds2 = dataset.get(ds2id)
        self.assertEqual(2, len(ds1["classes"][0]["recordings"]))
        self.assertEqual(1, len(ds2["classes"][0]["recordings"]))

    def test_add_class(self):
        """ Add a class to a dataset """

        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #3",
            "description": "This is the description of class 3"
        }

        originaldataset = dataset.get(dsid)
        dataset.add_class(dsid, test_data)
        updateddataset = dataset.get(dsid)

        self.assertEqual(2, len(originaldataset["classes"]))
        self.assertEqual(3, len(updateddataset["classes"]))
        expected = copy.deepcopy(test_data)
        expected["recordings"] = []
        expected["id"] = mock.ANY
        self.assertDictEqual(expected, updateddataset["classes"][2])

    def test_add_class_with_recordings(self):
        """ Add a class to a dataset and also add some recordings to it """

        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #3",
            "description": "This is description of class 3",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        dataset.add_class(dsid, test_data)
        updateddataset = dataset.get(dsid)

        # Check that both the class details and recordings are in the retrieved dataset
        expected = copy.deepcopy(test_data)
        expected["id"] = mock.ANY
        self.assertDictEqual(expected, updateddataset["classes"][2])

    def test_add_class_twice(self):
        """ A class name which already exists is skipped. """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #1",
            "description": "This is description of class 1",
            "recordings": ["1c085555-3805-428a-982f-e14e0a2b18e6"]
        }
        dataset.add_class(dsid, test_data)
        updateddataset = dataset.get(dsid)

        # Class #1 is not added again, but the recording is added to it
        self.assertEqual(2, len(updateddataset["classes"]))
        expected_recordings = ["0dad432b-16cc-4bf0-8961-fd31d124b01b",
                               "19e698e7-71df-48a9-930e-d4b1a2026c82",
                               "1c085555-3805-428a-982f-e14e0a2b18e6"]
        self.assertEqual(set(expected_recordings), set(updateddataset["classes"][0]["recordings"]))

    def test_delete_class(self):
        """ Delete a class from the dataset """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #2"
        }
        originaldataset = dataset.get(dsid)
        dataset.delete_class(dsid, test_data)
        updateddataset = dataset.get(dsid)

        self.assertEqual(2, len(originaldataset["classes"]))
        self.assertEqual(1, len(updateddataset["classes"]))

    def test_delete_nonexistent_class(self):
        """ Delete a class which doesn't exist in the dataset """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #100"
        }
        originaldataset = dataset.get(dsid)
        dataset.delete_class(dsid, test_data)
        updateddataset = dataset.get(dsid)

        self.assertEqual(2, len(originaldataset["classes"]))
        self.assertEqual(2, len(updateddataset["classes"]))

    def test_update_class(self):
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #1",
            "new_name": "Different class",
            "description": "different desc"
        }
        originaldataset = dataset.get(dsid)
        dataset.update_class(dsid, "Class #1", test_data)
        updateddataset = dataset.get(dsid)

        self.assertEqual("Class #2", updateddataset["classes"][1]["name"])
        self.assertEqual("", updateddataset["classes"][1]["description"])

        self.assertEqual("Class #1", originaldataset["classes"][0]["name"])
        self.assertEqual("Different class", updateddataset["classes"][0]["name"])
        self.assertEqual("different desc", updateddataset["classes"][0]["description"])

    def test_update_class_no_class(self):
        """ Return error if the class doesn't exist """
        dsid = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        test_data = {
            "name": "Class #1",
            "new_name": "Different class",
            "description": "different desc"
        }
        with self.assertRaises(db.exceptions.NoDataFoundException):
            dataset.update_class(dsid, "Class #99", test_data)

    def test_check_recording_in_dataset(self):
        dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        recording_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"

        resp = dataset.check_recording_in_dataset(dataset_id, recording_mbid)
        self.assertTrue(resp)

        recording_mbid = "770cc467-8dde-4d22-bc4c-a42f91e7515e"
        resp = dataset.check_recording_in_dataset(dataset_id, recording_mbid)
        self.assertFalse(resp)


class GetPublicDatasetsTestCase(AcousticbrainzTestCase):
    """A whole testcase because there are lots of cases to test"""

    def setUp(self):
        super(GetPublicDatasetsTestCase, self).setUp()

    def _create_user(self, name):
        """Creates a user with a given name and returns its id"""
        query = text("""insert into "user" (musicbrainz_id) values (:name) returning id""")
        with db.engine.connect() as connection:
            res = connection.execute(query, {"name": name})
            return res.fetchone()[0]

    def _create_dataset(self, author_id, name, desc="", public=True):
        """Creates a dataset for an author with a name and returns its id"""

        dataset_id = str(uuid.uuid4())
        query = text("""insert into dataset (id, name, description, author, public) values
            (:id, :name, :desc, :author, :public) returning id""")
        with db.engine.connect() as connection:
            res = connection.execute(query, {"id": dataset_id, "name": name,
                 "desc": desc, "author": author_id, "public": public})
            return res.fetchone()[0]

    def _create_dataset_job(self, dataset_id, status):
        """Create a job for a dataset with a given status"""
        dataset_job_id = str(uuid.uuid4())
        snapshot_id = db.dataset.create_snapshot(dataset_id)
        with db.engine.connect() as connection:
            res = connection.execute(text("""
                INSERT INTO dataset_eval_jobs (id, snapshot_id, status)
                     VALUES (:id, :snapshot_id, :status)
                  RETURNING id
            """), {
                "id": dataset_job_id,
                "snapshot_id": snapshot_id,
                "status": status,
            })
            return res.fetchone()[0]

    def _update_dataset_job(self, dataset_job_id, status, updated=None):
        """Update a job to a given status. If a time is provided,
        change updated to that time"""

        query = text("""update dataset_eval_jobs set status=:status
                where id = :id""")
        with db.engine.connect() as connection:
            connection.execute(query, {"id": dataset_job_id,
                 "status": status})

    #####

    def test_get_datasets(self):
        user1_id = self._create_user("myuser1")
        dataset1_id = self._create_dataset(user1_id, "test dataset1")
        self._create_dataset_job(dataset1_id, "pending")

        user2_id = self._create_user("myuser2")
        dataset2_id = self._create_dataset(user2_id, "test dataset2")
        self._create_dataset_job(dataset2_id, "running")

        datasets = dataset.get_public_datasets("all")
        self.assertEqual(2, len(datasets))

    def test_get_datasets_not_submitted(self):
        """ If a dataset has no jobs submitted, it should not show up"""

        user1_id = self._create_user("myuser1")
        dataset1_id = self._create_dataset(user1_id, "unsubmitted dataset")
        dataset2_id = self._create_dataset(user1_id, "submitted dataset")
        self._create_dataset_job(dataset2_id, "pending")
        datasets = dataset.get_public_datasets("all")

        self.assertEqual(1, len(datasets))
        self.assertEqual("submitted dataset", datasets[0]["name"])

    def test_get_datasets_not_public(self):
        """ If a dataset is not public, even if it has a job, it shouldn't
            show up."""

        user1_id = self._create_user("myuser1")
        dataset1_id = self._create_dataset(user1_id, "private dataset", public=False)
        self._create_dataset_job(dataset1_id, "pending")

        datasets = dataset.get_public_datasets("all")
        self.assertEqual(0, len(datasets))

    def test_get_datasets_submitted_multiple(self):
        """ If a dataset has been submitted many times, only the most recent submission
            status should show up"""

        user1_id = self._create_user("myuser1")
        dataset1_id = self._create_dataset(user1_id, "dataset")
        self._create_dataset_job(dataset1_id, "done")
        self._create_dataset_job(dataset1_id, "pending")

        datasets = dataset.get_public_datasets("all")
        self.assertEqual(1, len(datasets))
        self.assertEqual("pending", datasets[0]["status"])

    def test_get_datasets_filter_status(self):
        """ Filter datasets by the status of their jobs """

        user1_id = self._create_user("myuser1")
        dataset1_id = self._create_dataset(user1_id, "dataset1")
        self._create_dataset_job(dataset1_id, "pending")
        dataset2_id = self._create_dataset(user1_id, "dataset2")
        self._create_dataset_job(dataset2_id, "running")
        dataset3_id = self._create_dataset(user1_id, "dataset3")
        self._create_dataset_job(dataset3_id, "done")
        dataset4_id = self._create_dataset(user1_id, "dataset4")
        self._create_dataset_job(dataset4_id, "failed")

        datasets = dataset.get_public_datasets("all")
        self.assertEqual(4, len(datasets))

        datasets = dataset.get_public_datasets("pending")
        self.assertEqual(1, len(datasets))
        self.assertEqual("dataset1", datasets[0]["name"])

        datasets = dataset.get_public_datasets("running")
        self.assertEqual(1, len(datasets))
        self.assertEqual("dataset2", datasets[0]["name"])

        datasets = dataset.get_public_datasets("done")
        self.assertEqual(1, len(datasets))
        self.assertEqual("dataset3", datasets[0]["name"])

        datasets = dataset.get_public_datasets("failed")
        self.assertEqual(1, len(datasets))
        self.assertEqual("dataset4", datasets[0]["name"])

    def test_invalid_status(self):
        with self.assertRaises(ValueError):
            datasets = dataset.get_public_datasets("not_a_status")
