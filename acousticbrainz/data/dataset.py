import psycopg2
import copy
import jsonschema
from flask import current_app
from werkzeug.exceptions import BadRequest, ServiceUnavailable

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
        "description": {"type": "string"},
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
                    "description": {"type": "string"},
                    "recordings": {
                        # CLASS_MEMBER
                        "type": "array",
                        "items": {"type": "string"},  # FIXME: This should be a UUID
                    },
                },
            },
        },
    },
}

JSON_SCHEMA_COMPLETE = copy.deepcopy(BASE_JSON_SCHEMA)
# Must have at least two classes with at least one recording in each.
JSON_SCHEMA_COMPLETE["properties"]["classes"]["minItems"] = 2
JSON_SCHEMA_COMPLETE["properties"]["classes"]["items"]["properties"]["recordings"]["minItems"] = 2


def create_from_dict(dictionary, author_id=None):
    """Creates a new dataset from a dictionary.

    Returns:
        Tuple with two values: new dataset ID and error. If error occurs first
        will be None and second is an exception. If there are no errors, second
        value will be None.
    """
    jsonschema.validate(dictionary, BASE_JSON_SCHEMA)

    connection = psycopg2.connect(current_app.config["PG_CONNECT"])
    cursor = connection.cursor()

    cursor.execute("""INSERT INTO dataset (id, name, description, author)
                      VALUES (uuid_generate_v4(), %s, %s, %s) RETURNING id""",
                   (dictionary["name"], dictionary["description"], author_id))
    dataset_id = cursor.fetchone()[0]

    for cls in dictionary["classes"]:
        cursor.execute("""INSERT INTO class (name, description, dataset)
                          VALUES (%s, %s, %s) RETURNING id""",
                       (cls["name"], cls["description"], dataset_id))
        cls_id = cursor.fetchone()[0]

        for recording_mbid in cls["recordings"]:
            cursor.execute("INSERT INTO class_member (class, mbid) VALUES (%s, %s)",
                           (cls_id, recording_mbid))

    # If anything bad happens above, it should just rollback by default.
    connection.commit()

    return dataset_id


def update(dataset_id, dictionary, author_id):
    jsonschema.validate(dictionary, BASE_JSON_SCHEMA)

    connection = psycopg2.connect(current_app.config["PG_CONNECT"])
    cursor = connection.cursor()

    cursor.execute("""UPDATE dataset
                      SET (name, description, author) = (%s, %s, %s)
                      WHERE id = %s""",
                   (dictionary["name"], dictionary["description"], author_id, dataset_id))

    # Replacing old classes with new ones
    cursor.execute("""DELETE FROM class WHERE dataset = %s""", (dataset_id,))

    for cls in dictionary["classes"]:
        cursor.execute("""INSERT INTO class (name, description, dataset)
                          VALUES (%s, %s, %s) RETURNING id""",
                       (cls["name"], cls["description"], dataset_id))
        cls_id = cursor.fetchone()[0]

        for recording_mbid in cls["recordings"]:
            cursor.execute("INSERT INTO class_member (class, mbid) VALUES (%s, %s)",
                           (cls_id, recording_mbid))

    # If anything bad happens above, it should just rollback by default.
    connection.commit()


def get(id):
    """Get dataset with a specified ID.

    Returns:
        Dictionary with dataset details if it has been found, None
        otherwise.
    """
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("""SELECT id, name, description, author, created
                          FROM dataset
                          WHERE id = %s""",
                       (str(id),))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    if cursor.rowcount > 0:
        row = cursor.fetchone()
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "author": row[3],
            "created": row[4],
            "classes": get_classes(row[0]),
        }
    else:
        return None


def get_classes(dataset_id):
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("""SELECT id, name, description
                          FROM class
                          WHERE dataset = %s""",
                       (dataset_id,))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    rows = cursor.fetchall()
    classes = []
    for row in rows:
        classes.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "recordings": get_recordings_in_class(row[0])
        })
    return classes


def get_recordings_in_class(class_id):
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("""SELECT mbid FROM class_member WHERE class = %s""",
                       (class_id,))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    rows = cursor.fetchall()
    recordings = []
    for row in rows:
        recordings.append(row[0])
    return recordings


def get_by_user_id(user_id):
    """Get datasets created by a specified user.

    Returns:
        List of dictionaries with dataset details.
    """
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("""SELECT id, name, description, author, created
                          FROM dataset
                          WHERE author = %s""",
                       (user_id,))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return [{
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "author": row[3],
        "created": row[4],
    } for row in cursor.fetchall()]


def delete(id):
    """Delete dataset with a specified ID."""
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dataset WHERE id = %s", (str(id),))
        connection.commit()
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))
