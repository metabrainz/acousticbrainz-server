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
