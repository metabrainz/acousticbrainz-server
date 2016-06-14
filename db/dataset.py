import db
import db.dataset_eval
from utils import dataset_validator

from db import exceptions
import re
from sqlalchemy import text
import unicodedata


def _slugify(string):
    """Converts unicode string to lowercase, removes alphanumerics and
    underscores, and converts spaces to hyphens. Also strips leading and
    trailing whitespace.
    """
    string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    string = re.sub('[^\w\s-]', '', string).strip().lower()
    return re.sub('[-\s]+', '-', string)


def create_from_dict(dictionary, author_id):
    """Creates a new dataset from a dictionary.

    Returns:
        Tuple with two values: new dataset ID and error. If error occurs first
        will be None and second is an exception. If there are no errors, second
        value will be None.
    """
    dataset_validator.validate(dictionary)

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

            # Removing duplicate recordings
            cls["recordings"] = list(set(cls["recordings"]))

            for recording_mbid in cls["recordings"]:
                connection.execute("INSERT INTO dataset_class_member (class, mbid) VALUES (%s, %s)",
                               (cls_id, recording_mbid))

    return dataset_id


def update(dataset_id, dictionary, author_id):
    # TODO(roman): Make author_id argument optional (keep old author if None).
    dataset_validator.validate(dictionary)

    with db.engine.begin() as connection:
        if "description" not in dictionary:
            dictionary["description"] = None

        connection.execute("""UPDATE dataset
                          SET (name, description, public, author, last_edited) = (%s, %s, %s, %s, now())
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
            "SELECT id::text, name, description, author, created, public, last_edited "
            "FROM dataset "
            "WHERE id = %s",
            (str(id),)
        )
        if result.rowcount < 1:
            raise exceptions.NoDataFoundException("Can't find dataset with a specified ID.")
        row = dict(result.fetchone())
        row["classes"] = _get_classes(row["id"])
        return row


def get_public_datasets(status):
    if status == "all":
        statuses = db.dataset_eval.VALID_STATUSES
    elif status in db.dataset_eval.VALID_STATUSES:
        statuses = [status]
    else:
        raise ValueError("Unknown status")

    with db.engine.connect() as connection:
        query = text("""
            SELECT dataset.id::text
                 , dataset.name
                 , dataset.description
                 , "user".musicbrainz_id AS author_name
                 , dataset.created
                 , job.status
            FROM dataset
            JOIN "user"
              ON "user".id = dataset.author
              LEFT JOIN LATERAL (SELECT status
                                   FROM dataset_eval_jobs
                                  WHERE dataset.id = dataset_eval_jobs.dataset_id
                               ORDER BY updated DESC
                               LIMIT 1)
                               AS JOB ON TRUE
          WHERE dataset.public = 't'
            AND job.status = ANY((:status)::eval_job_status[])
       ORDER BY dataset.created DESC
             """)
        res = connection.execute(query, {"status": statuses})
        datasets = []
        for row in res:
            datasets.append(dict(row))

        return datasets


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
