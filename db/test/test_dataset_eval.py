from db.testing import DatabaseTestCase
from db import dataset, user, dataset_eval
import json


class DatasetEvalTestCase(DatabaseTestCase):

    def setUp(self):
        super(DatasetEvalTestCase, self).setUp()

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
        self.test_dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

    def test_create_job(self):
        job_id = dataset_eval._create_job(self.test_dataset_id)
        job = dataset_eval.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)

    def test_get_job(self):
        job_id = dataset_eval._create_job(self.test_dataset_id)
        job = dataset_eval.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(type(job), dict)

        self.assertIsNone(dataset_eval.get_job("f47ac10b-58cc-4372-a567-0e02b2c3d479"))

    def test_set_job_result(self):
        job_id = dataset_eval._create_job(self.test_dataset_id)

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
        job_id = dataset_eval._create_job(self.test_dataset_id)
        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_PENDING)

        dataset_eval.set_job_status(
            job_id=job_id,
            status=dataset_eval.STATUS_FAILED,
        )
        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_FAILED)

    def test_get_next_pending_job(self):
        job1_id = dataset_eval._create_job(self.test_dataset_id)
        job1 = dataset_eval.get_job(job1_id)

        job2_id = dataset_eval._create_job(self.test_dataset_id)
        job2 = dataset_eval.get_job(job2_id)

        next_pending = dataset_eval.get_next_pending_job()
        self.assertEqual(job1, next_pending)
        dataset_eval.set_job_status(
            job_id=job1_id,
            status=dataset_eval.STATUS_FAILED,
        )
        next_pending = dataset_eval.get_next_pending_job()
        self.assertEqual(job2, next_pending)

