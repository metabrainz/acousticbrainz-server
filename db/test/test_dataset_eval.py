import mock

from webserver.testing import AcousticbrainzTestCase
from db import dataset, user, dataset_eval
import db
import json


class DatasetEvalTestCase(AcousticbrainzTestCase):

    def setUp(self):
        super(DatasetEvalTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = user.create(self.test_user_mb_name)
        self.test_uuid = "123e4567-e89b-12d3-a456-426655440000"
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
        self.test_dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        self.conn = db.engine.connect()

    def test_validate_dataset_structure(self):
        test_dataset = {"classes": [
            {"name": "class1",
             # structure of recordings isn't important, only size
             "recordings": ["rec1", "rec2"]}
        ]}
        with self.assertRaises(dataset_eval.IncompleteDatasetException) as e:
            dataset_eval.validate_dataset_structure(test_dataset)
        self.assertEqual(str(e.exception), "Dataset needs to have at least 2 classes.")

        test_dataset["classes"].append(
            {"name": "class2",
             "recordings": ["rec1"]}
        )

        with self.assertRaises(dataset_eval.IncompleteDatasetException) as e:
            dataset_eval.validate_dataset_structure(test_dataset)
        self.assertEqual(str(e.exception), "There are not enough recordings in a class `class2` (1). At least 2 are required in each class.")

        test_dataset["classes"][1]["recordings"].append("rec2")

        # Shouldn't raise an exception
        dataset_eval.validate_dataset_structure(test_dataset)

    @mock.patch("db.data.count_lowlevel")
    def test_validate_dataset_contents(self, count_lowlevel):
        count_lowlevel.return_value = 1

        dataset_eval.validate_dataset_contents(self.test_data)

        calls = [mock.call("0dad432b-16cc-4bf0-8961-fd31d124b01b"),
                 mock.call("19e698e7-71df-48a9-930e-d4b1a2026c82"),
                 mock.call("fd528ddb-411c-47bc-a383-1f8a222ed213"),
                 mock.call("96888f9e-c268-4db2-bc13-e29f8b317c20"),
                 mock.call("ed94c67d-bea8-4741-a3a6-593f20a22eb6")]
        count_lowlevel.assert_has_calls(calls)

        count_lowlevel.return_value = 0
        with self.assertRaises(dataset_eval.IncompleteDatasetException) as e:
            dataset_eval.validate_dataset_contents(self.test_data)
        self.assertEqual(str(e.exception), "Can't find low-level data for recording: 0dad432b-16cc-4bf0-8961-fd31d124b01b")

    def test_create_job_nonormalize(self):
        # No dataset normalization
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, False, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["normalize"], False)

    def test_create_job_normalize(self):
        # dataset normalization
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["normalize"], True)

    def test_create_job_artistfilter(self):
        # Artist filtering as an option
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, False, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=dataset_eval.FILTER_ARTIST)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["filter_type"], "artist")

    def test_create_job_svm_params(self):
        # C, gamma, and preprocessing values
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=dataset_eval.FILTER_ARTIST)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["c_values"], [1, 2, 3])
        self.assertEqual(job["options"]["gamma_values"], [4, 5, 6])
        self.assertEqual(job["options"]["preprocessing_values"], ["basic"])

    def test_create_job_badfilter(self):
        # An unknown filter type
        with self.assertRaises(ValueError):
            dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                     c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                     filter_type="test")

    def test_create_job_badlocation(self):
        # an invalid eval_location
        with self.assertRaises(ValueError):
            dataset_eval._create_job(self.conn, self.test_dataset_id, True, "not_a_location",
                                     c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                     filter_type=None)

    def test_job_exists(self):
        self.assertFalse(dataset_eval.job_exists(self.test_dataset_id))
        dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                 c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                 filter_type=None)

        self.assertTrue(dataset_eval.job_exists(self.test_dataset_id))

    def test_get_job(self):
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        random_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        # just in case
        self.assertNotEqual(random_id, job_id)

        self.assertIsNone(dataset_eval.get_job(random_id))

    def test_set_job_result(self):
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)

        result = {
            u"accuracy": 1,
            u"parameters": {},
            u"confusion_matrix": {},
        }
        dataset_eval.set_job_result(
            job_id=job_id,
            result=json.dumps(result),
        )

        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["result"], result)

    def test_set_job_status(self):
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)

        dataset_eval.set_job_status(
            job_id=job_id,
            status=dataset_eval.STATUS_FAILED,
        )
        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_FAILED)

    def test_get_next_pending_job(self):
        job1_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                           c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                           filter_type=None)
        job1 = dataset_eval.get_job(job1_id)

        job2_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                           c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                           filter_type=None)
        job2 = dataset_eval.get_job(job2_id)

        next_pending = dataset_eval.get_next_pending_job()

        self.assertEqual(job1, next_pending)
        dataset_eval.set_job_status(
            job_id=job1_id,
            status=dataset_eval.STATUS_FAILED,
        )
        next_pending = dataset_eval.get_next_pending_job()
        self.assertEqual(job2, next_pending)

    def test_get_next_pending_job_remote(self):
        # If we have a remote pending job with the most recent timestamp, skip it
        job1_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_REMOTE,
                                           c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                           filter_type=None)
        job1 = dataset_eval.get_job(job1_id)

        job2_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                           c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                           filter_type=None)
        job2 = dataset_eval.get_job(job2_id)

        next_pending = dataset_eval.get_next_pending_job()
        self.assertEqual(job2, next_pending)

    def test_delete_job(self):
        with self.assertRaises(dataset_eval.JobNotFoundException):
            dataset_eval.delete_job(self.test_uuid)

        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        snapshots = dataset.get_snapshots_for_dataset(self.test_dataset_id)
        self.assertEqual(len(snapshots), 1)
        self.assertIsNotNone(dataset_eval.get_job(job_id))
        dataset_eval.delete_job(job_id)
        snapshots = dataset.get_snapshots_for_dataset(self.test_dataset_id)
        self.assertEqual(len(snapshots), 0)
        self.assertIsNone(dataset_eval.get_job(job_id))

    def test_eval_job_location(self):
        job1_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_REMOTE,
                                           c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                           filter_type=None)
        job1 = dataset_eval.get_job(job1_id)
        self.assertEqual(job1["eval_location"], dataset_eval.EVAL_REMOTE)

        job2_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                           c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                           filter_type=None)
        job2 = dataset_eval.get_job(job2_id)
        self.assertEqual(job2["eval_location"], dataset_eval.EVAL_LOCAL)

    def test_get_remote_pending_jobs_for_user(self):
        """ Check that we get remote pending jobs for a user """

        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_REMOTE,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        job_details = db.dataset_eval.get_job(job_id)

        response = dataset_eval.get_remote_pending_jobs_for_user(self.test_user_id)
        expected_response = [{
                'job_id' : str(job_id),
                'dataset_name' : self.test_data['name'],
                'created' : job_details['created']
                }]
        self.assertEqual(response, expected_response)

    def test_get_pending_jobs_for_user_local(self):
        """ Check that a local eval dataset for this user doesn't show """
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        job_details = db.dataset_eval.get_job(job_id)

        response = dataset_eval.get_remote_pending_jobs_for_user(self.test_user_id)
        self.assertEqual(response, [])

    def test_get_pending_jobs_for_user_other_user(self):
        """ Check that a remote eval job for another user doesn't show """

        another_user_id = user.create("another user")
        another_dataset_id = dataset.create_from_dict(self.test_data, author_id=another_user_id)
        job_id = dataset_eval._create_job(self.conn, another_dataset_id, True, dataset_eval.EVAL_REMOTE,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)

        response = dataset_eval.get_remote_pending_jobs_for_user(self.test_user_id)
        self.assertEqual(response, [])

    def test_get_pending_jobs_for_user_done(self):
        """ Check that a remote eval job with a done status doesn't show """
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_REMOTE,
                                          c_value=[1, 2, 3], gamma_value=[4, 5, 6], preprocessing_values=["basic"],
                                          filter_type=None)
        db.dataset_eval.set_job_status(job_id, db.dataset_eval.STATUS_DONE)

        response = dataset_eval.get_remote_pending_jobs_for_user(self.test_user_id)
        self.assertEqual(response, [])

    @mock.patch('db.dataset_eval.validate_dataset_contents')
    def test_evaluate_dataset(self, validate_dataset_contents):
        """Test that a dataset can be submitted for evaluation if it is complete"""

        dataset_eval.evaluate_dataset(self.test_dataset_id, False, 'local')
        self.assertTrue(dataset_eval.job_exists(self.test_dataset_id))

        # Evaluate a second time it will raise
        with self.assertRaises(dataset_eval.JobExistsException):
            dataset_eval.evaluate_dataset(self.test_dataset_id, False, 'local')

        # We validate after checking if the dataset exists, so this will only
        # be called once
        validate_dataset_contents.assert_called_once()

    @mock.patch('db.dataset_eval._create_job')
    def test_evaluate_dataset_incomplete(self, create_job):
        """Check that if the validation of a dataset fails it is not added."""

        # We just assume that the validation fails because there is no
        # low-level data for the recordings in this dataset
        with self.assertRaises(dataset_eval.IncompleteDatasetException):
            dataset_eval.evaluate_dataset(self.test_dataset_id, False, 'local')

        create_job.assert_not_called()
