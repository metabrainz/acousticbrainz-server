import unittest
from utils import dataset_validator


class DatasetValidatorTestCase(unittest.TestCase):

    def test_recordings_add_delete(self):
        """ Validator for requests to add or delete recordings from a class """

        # not a dictionary
        with self.assertRaises(dataset_validator.ValidationException) as e:
            out = e
            dataset_validator.validate_recordings_add_delete("not_dictionary")
        self.assertEqual(out.exception.message, "Request must be a dictionary.")

        # missing a required element
        with self.assertRaises(dataset_validator.ValidationException) as e:
            out = e
            dataset_validator.validate_recordings_add_delete({"class_name": "Test"})
        self.assertEqual(out.exception.message, "Field `recordings` is missing from recordings dictionary.")

        with self.assertRaises(dataset_validator.ValidationException) as e:
            out = e
            dataset_validator.validate_recordings_add_delete({"class_name": "Test", "recordings": [], "other": None})
        self.assertEqual(out.exception.message, "Unexpected field `other` in recordings dictionary.")

        # recordings not a list
        with self.assertRaises(dataset_validator.ValidationException) as e:
            out = e
            dataset_validator.validate_recordings_add_delete({"class_name": "Test", "recordings": "notlist"})
        self.assertEqual(out.exception.message, 'Field `recordings` in class "Test" is not a list.')

        # recording item not a uuid
        with self.assertRaises(dataset_validator.ValidationException) as e:
            out = e
            dataset_validator.validate_recordings_add_delete({"class_name": "Test", "recordings": [1]})
        self.assertEqual(out.exception.message, '"1" is not a valid recording MBID in class "Test".')

        # all ok
        dataset_validator.validate_recordings_add_delete({"class_name": "Test", "recordings": ["cc355a8a-1cf0-4eda-a693-fd38dc1dd4e2"]})

    def test_class(self):
        """ Validator for requests to add or delete a class """
        # Class validation is also tested in other tests below

        # recordings required depending on flag
        with self.assertRaises(dataset_validator.ValidationException) as e:
            out = e
            dataset_validator.validate_class({"name": "Test", "description": "Desc"}, recordings_required=True)
        self.assertEqual(out.exception.message, "Field `recordings` is missing from class.")

        # Required=False, no error
        dataset_validator.validate_class({"name": "Test", "description": "Desc"}, recordings_required=False)

    def test_dataset_unexpected_items(self):
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

    def test_dataset_missing_values(self):
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

    def test_dataset_update(self):
        # All fields is OK
        dataset_validator.validate_dataset_update({"name": "dataset name",
                                                   "description": "description",
                                                   "public": True})
        # An empty dict is OK
        dataset_validator.validate_dataset_update({})

        # Extra field
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate_dataset_update({"anotherfield": "value"})

        # Name too short
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate_dataset_update({"name": ""})

        # desc must be string
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate_dataset_update({"description": 1})

        # public must be boolean
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate_dataset_update({"public": "true"})



    def test_dataset_incorrect_types(self):
        # Incorrect types

        # String, not dict
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate("dataset")

        # Name should be string
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": ["This", "is", "my", "cool", "dataset"],
                "classes": [],
                "public": False,
            })

        # Desc should be string
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "description": False,
                "classes": [],
                "public": False,
            })

        # Classes should be list
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "description": "",
                "classes": None,
                "public": False,
            })

        # public should be bool
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "description": "",
                "classes": [],
                "public": "Nope",
            })

        # class name should be string
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

        # class elements should be dict
        with self.assertRaises(dataset_validator.ValidationException):
            dataset_validator.validate({
                "name": "test",
                "classes": [
                    "first",
                    "second",
                ],
                "public": False,
            })

        # Class desc should be string
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

        # class recordings should be list
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

        # Class recordings should be uuids
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

    def test_dataset_item_lengths(self):
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
