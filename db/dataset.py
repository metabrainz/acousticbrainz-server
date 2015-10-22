import db
import copy
import jsonschema


# JSON schema is used for validation of submitted datasets. BASE_JSON_SCHEMA
# defines basic structure of a dataset. JSON_SCHEMA_COMPLETE adds additional
# constraints required for further processing of a dataset. More information
# about JSON schema is available at http://json-schema.org/.

BASE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "description": {"type": ["string", "null"]},
        "public": {"type": "boolean"},
        "classes": {
            "type": "array",
            "items": {
                # CLASS
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "description": {"type": ["string", "null"]},
                    "recordings": {
                        # CLASS_MEMBER
                        "type": "array",
                        "items": {
                            # UUID (MusicBrainz ID)
                            "type": "string",
                            "pattern": "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
                        },
                    },
                },
                "required": [
                    "name",
                    "recordings",
                ],
            },
        },
    },
    "required": [
        "name",
        "classes",
        "public",
    ],
}

JSON_SCHEMA_COMPLETE = copy.deepcopy(BASE_JSON_SCHEMA)
# Must have at least two classes with at least one recording in each.
JSON_SCHEMA_COMPLETE["properties"]["classes"]["minItems"] = 2
JSON_SCHEMA_COMPLETE["properties"]["classes"]["items"]["properties"]["recordings"]["minItems"] = 2
# Keep in mind that we still need to manually check if all recordings are in
# AcousticBrainz database!


def create_from_dict(dictionary, author_id):
    """Creates a new dataset from a dictionary.

    Returns:
        Tuple with two values: new dataset ID and error. If error occurs first
        will be None and second is an exception. If there are no errors, second
        value will be None.
    """
    jsonschema.validate(dictionary, BASE_JSON_SCHEMA)

    with db.engine.begin() as connection:
        if "description" not in dictionary:
            dictionary["description"] = None

        result = connection.execute("""INSERT INTO dataset (id, name, description, public, author)
                          VALUES (uuid_generate_v4(), %s, %s, %s, %s) RETURNING id""",
                       (dictionary["name"], dictionary["description"], dictionary["public"], author_id))
        dataset_id = result.fetchone()[0]

        for cls in dictionary["classes"]:
            if "description" not in cls:
                cls["description"] = None
            result = connection.execute("""INSERT INTO dataset_class (name, description, dataset)
                              VALUES (%s, %s, %s) RETURNING id""",
                           (cls["name"], cls["description"], dataset_id))
            cls_id = result.fetchone()[0]

            for recording_mbid in cls["recordings"]:
                connection.execute("INSERT INTO dataset_class_member (class, mbid) VALUES (%s, %s)",
                               (cls_id, recording_mbid))

    return dataset_id


def update(dataset_id, dictionary, author_id):
    # TODO(roman): Make author_id argument optional (keep old author if None).
    jsonschema.validate(dictionary, BASE_JSON_SCHEMA)

    with db.engine.begin() as connection:
        if "description" not in dictionary:
            dictionary["description"] = None

        connection.execute("""UPDATE dataset
                          SET (name, description, public, author) = (%s, %s, %s, %s)
                          WHERE id = %s""",
                       (dictionary["name"], dictionary["description"], dictionary["public"], author_id, dataset_id))

        # Replacing old classes with new ones
        connection.execute("""DELETE FROM dataset_class WHERE dataset = %s""", (dataset_id,))

        for cls in dictionary["classes"]:
            if "description" not in cls:
                cls["description"] = None
            result = connection.execute("""INSERT INTO dataset_class (name, description, dataset)
                              VALUES (%s, %s, %s) RETURNING id""",
                           (cls["name"], cls["description"], dataset_id))
            cls_id = result.fetchone()[0]

            for recording_mbid in cls["recordings"]:
                connection.execute("INSERT INTO dataset_class_member (class, mbid) VALUES (%s, %s)",
                               (cls_id, recording_mbid))


def get(id):
    """Get dataset with a specified ID.

    Returns:
        Dictionary with dataset details if it has been found, None
        otherwise.
    """
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT id::text, name, description, author, created, public "
            "FROM dataset "
            "WHERE id = %s",
            (str(id),)
        )
        if result.rowcount > 0:
            row = dict(result.fetchone())
            row["classes"] = _get_classes(row["id"])
            return row
        else:
            return None


def _get_classes(dataset_id):
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT id::text, name, description "
            "FROM dataset_class "
            "WHERE dataset = %s",
            (dataset_id,)
        )
        rows = result.fetchall()
        classes = []
        for row in rows:
            row = dict(row)
            row["recordings"] = _get_recordings_in_class(row["id"])
            classes.append(row)
        return classes


def _get_recordings_in_class(class_id):
    with db.engine.connect() as connection:
        result = connection.execute("SELECT mbid::text FROM dataset_class_member WHERE class = %s",
                       (class_id,))
        recordings = []
        for row in result:
            recordings.append(row["mbid"])
        return recordings


def get_by_user_id(user_id, public_only=True):
    """Get datasets created by a specified user.

    Returns:
        List of dictionaries with dataset details.
    """
    with db.engine.connect() as connection:
        where = "WHERE author = %s"
        if public_only:
            where += " AND public = TRUE"
        result = connection.execute("SELECT id, name, description, author, created "
                       "FROM dataset " + where,
                       (user_id,))
        datasets = []
        for row in result:
            datasets.append(dict(row))
        return datasets


def delete(id):
    """Delete dataset with a specified ID."""
    with db.engine.begin() as connection:
        connection.execute("DELETE FROM dataset WHERE id = %s", (str(id),))
