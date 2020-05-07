from flask_uuid import UUID_RE
from six import string_types, ensure_text

DATASET_NAME_LEN_MIN = 1
DATASET_NAME_LEN_MAX = 100

CLASS_NAME_LEN_MIN = 1
CLASS_NAME_LEN_MAX = 100


def validate(dataset):
    """Validator for datasets.

    Dataset must have the following structure:
    {
        - name (string)
        - description (string, optional)
        - classes (list of class dicts)
            {
                - name (string)
                - description (string, optional)
                - recordings (list of UUIDs)
            }
    }

    Complete dataset must contain at least two classes with two recordings in
    each class.

    Args:
        dataset: Dataset stored in a dictionary.

    Raises:
        ValidationException: A general exception for validation errors.
        IncompleteDatasetException: Raised in cases when one of "completeness"
            requirements is not satisfied.
    """
    if not isinstance(dataset, dict):
        raise ValidationException("Dataset must be a dictionary.")
    _check_dict_structure(
        dataset,
        [
            ("name", True),
            ("description", False),
            ("classes", True),
            ("public", True),
        ],
        "dataset dictionary",
    )

    # Name
    _validate_dataset_name(dataset["name"])

    # Description (optional)
    if "description" in dataset and dataset["description"] is not None:
        _validate_dataset_description(dataset["description"])

    # Classes
    _validate_classes(dataset["classes"])

    # Publicity
    _validate_dataset_public(dataset["public"])


def _validate_dataset_name(name):
    """ Validate the name field of a dataset """
    if not isinstance(name, string_types):
        raise ValidationException("Field `name` must be a string.")
    if not (DATASET_NAME_LEN_MIN <= len(name) <= DATASET_NAME_LEN_MAX):
        raise ValidationException("Dataset name must be between %s and %s characters" %
                                  (DATASET_NAME_LEN_MIN, DATASET_NAME_LEN_MAX))


def _validate_dataset_description(description):
    """ Validate the description of a dataset """
    if not isinstance(description, string_types):
        raise ValidationException("Value of `description` in a dataset must be a string.")


def _validate_dataset_public(public):
    """ Validate the public field of a dataset """
    if not isinstance(public, bool):
        raise ValidationException('Value of `public` must be a boolean.')


def validate_dataset_update(dataset):
    if not isinstance(dataset, dict):
        raise ValidationException("Dataset must be a dictionary.")
    _check_dict_structure(
        dataset,
        [
            ("name", False),
            ("description", False),
            ("public", False),
        ],
        "dataset dictionary",
    )

    # Name
    if "name" in dataset:
        _validate_dataset_name(dataset["name"])

    # Description (optional)
    if "description" in dataset and dataset["description"] is not None:
        _validate_dataset_description(dataset["description"])

    # Publicity
    if "public" in dataset:
        _validate_dataset_public(dataset["public"])


def validate_class(cls, idx=None, recordings_required=True):
    """ Validate the contents of a class dictionary

    Args:
        cls: the class to check
        idx: the index of this class if it is part of a list of classes,
                otherwise None if it's a standalone class
        recordings_required: True if this class must have a `recordings` element

    Raises:
        ValidationException if the class structure doesn't match the requirements.
    """

    class_number_text = "" if idx is None else " number %s" % idx

    if not isinstance(cls, dict):
        raise ValidationException("Class%s is not a dictionary. All classes "
                                  "must be dictionaries." % class_number_text)
    _check_dict_structure(
        cls,
        [
            ("name", True),
            ("description", False),
            ("recordings", recordings_required),
        ],
        "class%s" % class_number_text,
    )

    # Name
    if not isinstance(cls["name"], string_types):
        raise ValidationException("Field `name` of class%s is not a string." % class_number_text)
    if not (CLASS_NAME_LEN_MIN <= len(cls["name"]) <= CLASS_NAME_LEN_MAX):
        raise ValidationException("Length of the `name` field in class%s doesn't fit the limits. "
                                  "Class name must be between %s and %s characters" %
                                  (class_number_text, CLASS_NAME_LEN_MIN, CLASS_NAME_LEN_MAX))

    # Description (optional)
    if "description" in cls and cls["description"] is not None:
        if not isinstance(cls["description"], string_types):
            class_number_text = "" if not idx else " (number %s)" % idx
            raise ValidationException('Field `description` in class "%s"%s is not a string.' %
                                      (cls["name"], class_number_text))

    # Recordings (optional if `recordings_required`=False, otherwise required)
    if "recordings" in cls:
        _validate_recordings(cls["recordings"], cls["name"], idx)


def validate_class_update(cls):
    """ Validate the contents of a definition for updating a dataset class

    :param cls: the class to check
    :raises: `ValidationException` if the class definition has a problem
    """

    if not isinstance(cls, dict):
        raise ValidationException("Class is not a dictionary. All classes "
                                  "must be dictionaries.")
    _check_dict_structure(
        cls,
        [
            ("name", True),
            ("new_name", False),
            ("description", False),
        ],
        "class",
    )

    # Name
    if not isinstance(cls["name"], string_types):
        raise ValidationException("Field `name` of class is not a string.")
    if "new_name" in cls and not isinstance(cls["new_name"], string_types):
        raise ValidationException("Field `new_name` of class is not a string.")
    if "new_name" in cls and not (CLASS_NAME_LEN_MIN <= len(cls["new_name"]) <= CLASS_NAME_LEN_MAX):
        raise ValidationException("Length of the `new_name` field in class doesn't fit the limits. "
                                  "Class name must be between %s and %s characters" %
                                  (CLASS_NAME_LEN_MIN, CLASS_NAME_LEN_MAX))

    # Description (optional)
    if "description" in cls and cls["description"] is not None:
        if not isinstance(cls["description"], string_types):
            raise ValidationException('Field `description` in class "%s" is not a string.' %
                                      (cls["name"], ))


def validate_recordings_add_delete(record_dict):
    """Validate for add/delete recordings"""
    if not isinstance(record_dict, dict):
        raise ValidationException("Request must be a dictionary.")
    _check_dict_structure(
        record_dict,
        [
            ("class_name", True),
            ("recordings", True),
        ],
        "recordings dictionary",
    )
    _validate_recordings(record_dict["recordings"], record_dict["class_name"], None)


def _validate_classes(classes):
    if not isinstance(classes, list):
        raise ValidationException("Field `classes` must be a list of strings.")
    for idx, cls in enumerate(classes):
        validate_class(cls, idx)


def _validate_recordings(recordings, cls_name, cls_index=None):
    """ Validate recordings

    Args:
        recordings: The recordings to validate
        cls_name: The name of the class these recordings are part of (for use in error messages)
        cls_index: A list index if these recordings are in a class which is part of a dataset
                      or None if the class is standalone (for use in error messages)

    Raises:
        ValidationException if the recordings definition has a problem
    """
    class_number_text = "" if not cls_index else " (number %s)" % cls_index
    if not isinstance(recordings, list):
        raise ValidationException('Field `recordings` in class "%s"%s is not a list.'
                                  % (cls_name, class_number_text))
    for recording in recordings:
        if not isinstance(recording, string_types) or not UUID_RE.match(ensure_text(recording)):
            raise ValidationException('"%s" is not a valid recording MBID in class "%s"%s.' %
                                      (recording, cls_name, class_number_text))


def _check_dict_structure(dictionary, keys, error_location):
    """Checks if dictionary contains only allowed values and, if necessary, if
    required items are missing.

    Args:
        dictionary: Dictionary that needs to be checked.
        keys: List of <name, required> tuples. `required` value must be a boolean:
            True if the field is required, False if not.
        error_location: Part of the error message that indicates where error occurs.

    Raises:
        ValidationException when dictionary structure doesn't match the requirements.
    """
    allowed_keys = [v[0] for v in keys]
    dict_keys = dictionary.keys()
    for k, req in keys:
        if req and k not in dict_keys:
            raise ValidationException("Field `%s` is missing from %s." % (k, error_location))
    for key in dict_keys:
        if key not in allowed_keys:
            raise ValidationException("Unexpected field `%s` in %s." % (key, error_location))


class ValidationException(Exception):
    """Base class for dataset validation exceptions."""
    def __init__(self, error, *args, **kwargs):
        """Create a new ValidationException

        Arguments:
            error: A description of why this error was raised
        """
        super(Exception, self).__init__(error, *args, **kwargs)
        self.error = error
