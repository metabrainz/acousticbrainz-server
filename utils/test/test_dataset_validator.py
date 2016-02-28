import unittest
from utils import dataset_validator


class DatasetValidatorTestCase(unittest.TestCase):

    def test_malformed_datasets(self):
        # Unexpected items
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "i_like": "to test",
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "i": "don't",
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "Dataset",
                "surname": "For Testing",  # this item shouldn't be there
                "classes": [
                    {
                        "name": "Not Rock",
                        "recordings": [],
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "Dataset",
                "classes": [
                    {
                        "name": "Rock",
                        "why": "Because",  # this item shouldn't be there
                        "recordings": [],
                    },
                ],
                "public": True,
            })

        # Missing values
        with self.assertRaises(dataset_validator.ValidationException):
            # Dataset name is missing
            dataset_validator.validate({
                "classes": [
                    {
                        "name": "the one and only",
                        "recordings": [],
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            # List of classes is missing
            dataset_validator.validate({
                "name": "test",
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            # Publicity value is missing
            dataset_validator.validate({
                "name": "test",
                "classes": [],
            })
        with self.assertRaises(dataset_validator.ValidationException):
            # Class name is missing
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "recordings": [],
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            # List of recordings in a class is missing
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "name": "this",
                    },
                ],
                "public": False,
            })

        # Incorrect types
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate("dataset")
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": ["This", "is", "my", "cool", "dataset"],
                "classes": [],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "description": False,
                "classes": [],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "description": "",
                "classes": None,
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "description": "",
                "classes": [],
                "public": "Nope",
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "name": ("this", "is", "a", "name"),
                        "recordings": [],
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    "first",
                    "second",
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "name": "first",
                        "description": False,
                        "recordings": [],
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "name": "first",
                        "recordings": "I don't have any :(",
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "name": "first",
                        "recordings": [
                            "my favourite"
                        ],
                    },
                ],
                "public": False,
            })

        # Incorrect lengths
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "",  # incorrect
                "classes": [],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "this dataset",
                "classes": [
                    {
                        "name": "",  # incorrect
                        "recordings": [],
                    },
                ],
                "public": False,
            })
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    {
                        "name": "Not Rock",
                        "why": "Because",  # this item shouldn't be there
                        "recordings": [],
                    },
                ],
                "public": False,
            })

    def test_validate_incomplete_datasets(self):
        # Not enough classes
        with self.assertRaises(dataset_validator.IncompleteDatasetException):
            dataset_validator.validate({
                "name": "Test",
                "classes": [
                    {
                        "name": "Class #1",
                        "recordings": [
                            "0dad432b-16cc-4bf0-8961-fd31d124b01b",
                            "19e698e7-71df-48a9-930e-d4b1a2026c82",
                        ]
                    },
                ],
                "public": True,
            }, complete=True)

        # Not enough recordings in a class
        with self.assertRaises(dataset_validator.IncompleteDatasetException):
            dataset_validator.validate({
                "name": "Test",
                "classes": [
                    {
                        "name": "Class #1",
                        "recordings": [
                            "0dad432b-16cc-4bf0-8961-fd31d124b01b",
                            "19e698e7-71df-48a9-930e-d4b1a2026c82",
                        ]
                    },
                    {
                        "name": "Class #2",
                        "recordings": [
                            "fd528ddb-411c-47bc-a383-1f8a222ed213",
                        ]
                    },
                ],
                "public": True,
            }, complete=True)

    def test_validate_complete_datasets(self):
        dataset_validator.validate({
            "name": "Test",
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
                    "recordings": [
                        "fd528ddb-411c-47bc-a383-1f8a222ed213",
                        "96888f9e-c268-4db2-bc13-e29f8b317c20",
                        "ed94c67d-bea8-4741-a3a6-593f20a22eb6",
                    ]
                },
            ],
            "public": True,
        })
