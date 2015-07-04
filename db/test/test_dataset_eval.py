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

        self.assertIsNone(dataset_eval.get_job("123e4567-e89b-12d3-a456-426655440000"))

    def test_set_job_results(self):
        job_id = dataset_eval._create_job(self.test_dataset_id)

        test_parameters = {u"parameters": 1}
        test_accuracy = {u"accuracy": 1}
        dataset_eval.set_job_results(
            job_id=job_id,
            parameters=json.dumps(test_parameters),
            accuracy=json.dumps(test_accuracy),
        )

        job = dataset_eval.get_job(job_id)
        self.assertEqual(job["status"], dataset_eval.STATUS_DONE)
        self.assertEqual(job["parameters"], test_parameters)
        self.assertEqual(job["accuracy"], test_accuracy)

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
