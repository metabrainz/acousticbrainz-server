import psycopg2
import copy
import jsonschema
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


def create_from_dict(dictionary, author_id):
    """Creates a new dataset from a dictionary.

    Returns:
        Tuple with two values: new dataset ID and error. If error occurs first
        will be None and second is an exception. If there are no errors, second
        value will be None.
    """
    jsonschema.validate(dictionary, BASE_JSON_SCHEMA)

    from acousticbrainz.data import connection
    cursor = connection.cursor()

    if "description" not in dictionary:
        dictionary["description"] = None

    cursor.execute("""INSERT INTO dataset (id, name, description, public, author)
                      VALUES (uuid_generate_v4(), %s, %s, %s, %s) RETURNING id""",
                   (dictionary["name"], dictionary["description"], dictionary["public"], author_id))
    dataset_id = cursor.fetchone()[0]

    for cls in dictionary["classes"]:
        if "description" not in cls:
            cls["description"] = None
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
    # TODO(roman): Make author_id argument optional (keep old author if None).
    jsonschema.validate(dictionary, BASE_JSON_SCHEMA)

    from acousticbrainz.data import connection
    cursor = connection.cursor()

    if "description" not in dictionary:
        dictionary["description"] = None

    cursor.execute("""UPDATE dataset
                      SET (name, description, public, author) = (%s, %s, %s, %s)
                      WHERE id = %s""",
                   (dictionary["name"], dictionary["description"], dictionary["public"], author_id, dataset_id))

    # Replacing old classes with new ones
    cursor.execute("""DELETE FROM class WHERE dataset = %s""", (dataset_id,))

    for cls in dictionary["classes"]:
        if "description" not in cls:
            cls["description"] = None
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
    from acousticbrainz.data import connection
    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT id, name, description, author, created, public
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
            "public": row[5],
            "classes": _get_classes(row[0]),
        }
    else:
        return None


def _get_classes(dataset_id):
    from acousticbrainz.data import connection
    try:
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
            "recordings": _get_recordings_in_class(row[0])
        })
    return classes


def _get_recordings_in_class(class_id):
    from acousticbrainz.data import connection
    try:
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


def get_by_user_id(user_id, public_only=True):
    """Get datasets created by a specified user.

    Returns:
        List of dictionaries with dataset details.
    """
    from acousticbrainz.data import connection
    try:
        cursor = connection.cursor()
        where = "WHERE author = %s"
        if public_only:
            where += " AND public = TRUE"
        cursor.execute("SELECT id, name, description, author, created "
                       "FROM dataset " + where,
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
    from acousticbrainz.data import connection
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dataset WHERE id = %s", (str(id),))
        connection.commit()
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))
