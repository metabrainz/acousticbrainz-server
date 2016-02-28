from flask_uuid import UUID_RE

DATASET_NAME_LEN_MIN = 1
DATASET_NAME_LEN_MAX = 100

MIN_CLASSES = 2
CLASS_NAME_LEN_MIN = 1
CLASS_NAME_LEN_MAX = 100

MIN_RECORDINGS_IN_CLASS = 2


def validate(dataset, complete=False):
    if not isinstance(dataset, dict):
        raise ValidationException("Dataset must be a dictionary.")
    _check_dict_structure(dataset, ["name", "description", "classes", "public"])

    # Name
    if "name" not in dataset:
        raise ValidationException("Dataset must have a name.")
    if not isinstance(dataset["name"], basestring):
        raise ValidationException("Class name must be a string.")
    if not (DATASET_NAME_LEN_MIN < len(dataset["name"]) < DATASET_NAME_LEN_MAX):
        raise ValidationException("Class name must be between %s and %s characters" %
                                  (DATASET_NAME_LEN_MIN, DATASET_NAME_LEN_MAX))

    # Description (optional)
    if "description" in dataset:
        if not isinstance(dataset["description"], basestring):
            raise ValidationException("Description must be a string.")
        # TODO: Do we need to check the length there?

    # Classes
    if "classes" not in dataset:
        raise ValidationException("Dataset must have a list of classes.")
    _validate_classes(dataset["classes"], complete)

    # Publicity
    if "public" not in dataset:
        raise ValidationException("You need to specify if dataset is public or not.")
    if not isinstance(dataset["public"], bool):
        raise ValidationException('Value "public" must be a boolean.')


def _validate_classes(classes, complete=False):
    if not isinstance(classes, list):
        raise ValidationException("Classes need to be in a list.")
    for cls in classes:
        _validate_class(cls, complete)

    if complete:
        if len(classes) < MIN_CLASSES:
            raise IncompleteDatasetException("Dataset needs to have at least %s classes." %
                                             MIN_CLASSES)


def _validate_class(cls, complete=False):
    if not isinstance(cls, dict):
        raise ValidationException("Class must be a dictionary.")
    _check_dict_structure(cls, ["name", "description", "recordings"])

    # Name
    if "name" not in cls:
        raise ValidationException("Each class must have a name.")
    if not isinstance(cls["name"], basestring):
        raise ValidationException("Class name must be a string.")
    if not (CLASS_NAME_LEN_MIN < len(cls["name"]) < CLASS_NAME_LEN_MAX):
        raise ValidationException("Class name must be between %s and %s characters" %
                                  (CLASS_NAME_LEN_MIN, CLASS_NAME_LEN_MIN))

    # Description (optional)
    if "description" in cls:
        if not isinstance(cls["description"], basestring):
            raise ValidationException("Description must be a string.")
        # TODO: Do we need to check the length there?

    # Recordings
    if "recordings" not in cls:
        raise ValidationException("Each class must have a list of recordings.")
    _validate_recordings(cls["recordings"], complete)


def _validate_recordings(recordings, complete=False):
    if not isinstance(recordings, list):
        raise ValidationException("Recordings need to be in a list.")
    for recording in recordings:
        if not UUID_RE.match(recording):
            raise ValidationException('"%s" is not a valid recording MBID.' % recording)

    if complete:
        if len(recordings) < MIN_RECORDINGS_IN_CLASS:
            # TODO: Would be nice to mention class name in an error message.
            raise IncompleteDatasetException("There are not enough recordings in a class (%s). "
                                             "At least %s are required in each class." %
                                             (len(recordings), MIN_RECORDINGS_IN_CLASS))


def _check_dict_structure(dictionary, allowed_keys):
    for key in dictionary.iterkeys():
        if key not in allowed_keys:
            raise ValidationException("Unexpected item: %s." % key)


class ValidationException(Exception):
    """Base class for dataset validation exceptions."""
    pass

class IncompleteDatasetException(ValidationException):
    pass
