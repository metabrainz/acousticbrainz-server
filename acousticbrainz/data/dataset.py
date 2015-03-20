import psycopg2
from flask import current_app
from werkzeug.exceptions import BadRequest, ServiceUnavailable


DATASET_JSON_SCHEMA = {
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
            "minItems": 2,  # must have at least two classes
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
                        "minItems": 1,  # must have at one recording
                        "items": {"type": "string"},  # FIXME: This should be a UUID
                    },
                },
            },
        },
    },
}


def create_from_dict(dictionary, owner_id=None):
    """Creates a new dataset from a dictionary.

    Data in the dictionary must be validated using `DATASET_JSON_SCHEMA` before
    being passed to this function.

    Returns:
        Tuple with two values: new dataset ID and error. If error occurs first
        will be None and second is an exception. If there are no errors, second
        value will be None.
    """
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()

        cursor.execute("""INSERT INTO dataset (id, name, description, owner)
                          VALUES (uuid_generate_v4(), %s, %s, %s) RETURNING id""",
                       (dictionary["name"], dictionary["description"], owner_id))
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

    except (psycopg2.ProgrammingError, psycopg2.IntegrityError, psycopg2.OperationalError) as e:
        # TODO: Log this.
        return None, e

    return dataset_id, None


def get(id):
    """Get dataset with a specified ID.

    Returns:
        Dictionary with dataset details if it has been found, None
        otherwise.
    """
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("""SELECT id, name, description, owner, created
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
            "owner": row[3],
            "created": row[4],
        }
    else:
        return None


def get_by_user_id(user_id):
    """Get datasets created by a specified user.

    Returns:
        List of dictionaries with dataset details.
    """
    try:
        connection = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = connection.cursor()
        cursor.execute("""SELECT id, name, description, owner, created
                          FROM dataset
                          WHERE owner = %s""",
                       (user_id,))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return [{
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "owner": row[3],
        "created": row[4],
    } for row in cursor.fetchall()]
