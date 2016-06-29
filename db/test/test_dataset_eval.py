from db.testing import DatabaseTestCase
from db import dataset, user, dataset_eval
import db
import json


class DatasetEvalTestCase(DatabaseTestCase):

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

    def test_create_job_nonormalize(self):
        # No dataset normalization
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, False, dataset_eval.EVAL_LOCAL)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["normalize"], False)

    def test_create_job_normalize(self):
        # dataset normalization
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["normalize"], True)

    def test_create_job_artistfilter(self):
        # Artist filtering as an option
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, False, dataset_eval.EVAL_LOCAL, dataset_eval.FILTER_ARTIST)
        job = dataset_eval.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)
        self.assertEqual(job["options"]["filter_type"], "artist")

    def test_create_job_badfilter(self):
        # An unknown filter type
        with self.assertRaises(ValueError):
            job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL, "test")

    def test_get_job(self):
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
        random_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        # just in case
        self.assertNotEqual(random_id, job_id)

        self.assertIsNone(dataset_eval.get_job(random_id))

    def test_set_job_result(self):
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)

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
        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)

        dataset_eval.set_job_status(
            job_id=job_id,
            status=dataset_eval.STATUS_FAILED,
        )
        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_FAILED)

    def test_get_next_pending_job(self):
        self.maxDiff = None
        job1_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
        job1 = dataset_eval.get_job(job1_id)

        job2_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
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
        job1_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_REMOTE)
        job1 = dataset_eval.get_job(job1_id)

        job2_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
        job2 = dataset_eval.get_job(job2_id)

        next_pending = dataset_eval.get_next_pending_job()
        self.assertEqual(job2, next_pending)

    def test_delete_job(self):
        with self.assertRaises(dataset_eval.JobNotFoundException):
            dataset_eval.delete_job(self.test_uuid)

        job_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL)
        snapshots = dataset.get_snapshots_for_dataset(self.test_dataset_id)
        self.assertEqual(len(snapshots), 1)
        self.assertIsNotNone(dataset_eval.get_job(job_id))
        dataset_eval.delete_job(job_id)
        snapshots = dataset.get_snapshots_for_dataset(self.test_dataset_id)
        self.assertEqual(len(snapshots), 0)
        self.assertIsNone(dataset_eval.get_job(job_id))

    def test_eval_job_location(self):
        job1_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_REMOTE, None)
        job1 = dataset_eval.get_job(job1_id)
        self.assertEqual(job1["eval_location"], dataset_eval.EVAL_REMOTE)

        job2_id = dataset_eval._create_job(self.conn, self.test_dataset_id, True, dataset_eval.EVAL_LOCAL, None)
        job2 = dataset_eval.get_job(job2_id)
        self.assertEqual(job2["eval_location"], dataset_eval.EVAL_LOCAL)
