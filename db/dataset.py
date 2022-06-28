import json
import re
import unicodedata

import sqlalchemy
from sqlalchemy import text

import db
import db.dataset_eval
from db import exceptions
from utils import dataset_validator


def slugify(string):
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
        if "description" not in dictionary or dictionary["description"] is None:
            dictionary["description"] = ""

        result = connection.execute("""INSERT INTO dataset (id, name, description, public, author)
                          VALUES (uuid_generate_v4(), %s, %s, %s, %s) RETURNING id""",
                                    (dictionary["name"], dictionary["description"], dictionary["public"], author_id))
        dataset_id = result.fetchone()[0]

        for cls in dictionary["classes"]:
            if "description" not in cls or cls["description"] is None:
                cls["description"] = ""
            result = connection.execute("""INSERT INTO dataset_class (name, description, dataset)
                              VALUES (%s, %s, %s) RETURNING id""",
                                        (cls["name"], cls["description"], dataset_id))
            cls_id = result.fetchone()[0]

            # Remove duplicate recordings, preserving order
            seen = set()
            cls["recordings"] = [r for r in cls["recordings"] if not (r in seen or seen.add(r))]

            for recording_mbid in cls["recordings"]:
                connection.execute("INSERT INTO dataset_class_member (class, mbid) VALUES (%s, %s)",
                                   (cls_id, recording_mbid))

    return dataset_id


def update_dataset_meta(dataset_id, meta):
    """ Update the metadata (name, description, public) for a dataset.

    Args:
        dataset_id: id of the dataset to update
        meta: dictionary of metadata to update

    Valid keys for `meta` are: `name`, `description`, `public`.
    If one of these keys is not present, the corresponding field
    for the dataset will not be updated. If no keys are present,
    the dataset will not be updated.
    """

    params = {}
    updates = []
    # Check meta values against None because "" and False are valid values
    name = meta.pop("name", None)
    if name is not None:
        updates.append("name = :name")
        params["name"] = name
    desc = meta.pop("description", None)
    if desc is not None:
        updates.append("description = :description")
        params["description"] = desc
    public = meta.pop("public", None)
    if public is not None:
        updates.append("public = :public")
        params["public"] = public

    if meta:
        raise ValueError("Unexpected meta value(s): %s" % ", ".join(meta.keys()))

    setstr = ", ".join(updates)
    query = text("""UPDATE dataset
                       SET %s
                     WHERE id = :id
            """ % setstr)

    # Only do an update if we have items to update
    if params:
        params["id"] = dataset_id
        with db.engine.begin() as connection:
            connection.execute(query, params)


def update(dataset_id, dictionary, author_id):
    # TODO(roman): Make author_id argument optional (keep old author if None).
    dataset_validator.validate(dictionary)

    with db.engine.begin() as connection:
        if "description" not in dictionary or dictionary["description"] is None:
            dictionary["description"] = ""

        connection.execute("""UPDATE dataset
                          SET (name, description, public, author, last_edited) = (%s, %s, %s, %s, now())
                          WHERE id = %s""",
                           (dictionary["name"], dictionary["description"], dictionary["public"], author_id, dataset_id))

        # Replacing old classes with new ones
        connection.execute("""DELETE FROM dataset_class WHERE dataset = %s""", (dataset_id,))

        for cls in dictionary["classes"]:
            if "description" not in cls or cls["description"] is None:
                cls["description"] = ""
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
        row["num_recordings"] = sum([len(cl.get("recordings", [])) for cl in row["classes"]])
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
              LEFT JOIN LATERAL (SELECT dataset_eval_jobs.status
                                   FROM dataset_eval_jobs
                                   JOIN dataset_snapshot
                                     ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
                                  WHERE dataset.id = dataset_snapshot.dataset_id
                               ORDER BY dataset_eval_jobs.updated DESC
                               LIMIT 1)
                               AS JOB ON TRUE
          WHERE dataset.public = 't'
            AND job.status = ANY((:status)::eval_job_status[])
       ORDER BY dataset.created DESC
             """)
        result = connection.execute(query, {"status": statuses})
        return [dict(row) for row in result]


def _get_classes(dataset_id):
    with db.engine.connect() as connection:
        query = text("""SELECT id::text
                             , name
                             , description
                          FROM dataset_class
                         WHERE dataset = :dataset_id
                      ORDER BY id
        """)
        result = connection.execute(query, {"dataset_id": dataset_id})
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


def create_snapshot(dataset_id):
    """Creates a snapshot of current version of a dataset.

    Snapshots are stored as JSON and have the following structure:
    {
        "name": "..",
        "description": "..",
        "classes": [
            {
                "name": "..",
                "description: "..",
                "recordings": ["..", ...]
            },
            ...
        ]
    }

    Args:
        dataset_id (string/uuid): ID of a dataset.

    Returns:
        ID (UUID) of a snapshot that was created.
    """
    dataset = get(dataset_id)
    if not dataset:
        raise exceptions.NoDataFoundException("Can't find dataset with a specified ID.")
    snapshot = {
        "name": dataset["name"],
        "description": dataset["description"],
        "classes": [{
                        "name": c["name"],
                        "description": c["description"],
                        "recordings": c["recordings"],
                    } for c in dataset["classes"]],
    }
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO dataset_snapshot (id, dataset_id, data)
                 VALUES (uuid_generate_v4(), :dataset_id, :data)
              RETURNING id::text
        """), {
            "dataset_id": dataset_id,
            "data": json.dumps(snapshot),
        })
        return result.fetchone()["id"]


def get_snapshot(id):
    """Get snapshot of a dataset.

    Args:
        id (string/uuid): ID of a snapshot.

    Returns:
        dictionary: {
            "id": <ID of the snapshot>,
            "dataset_id": <ID of the dataset that this snapshot is associated with>,
            "created": <creation time>,
            "data": <actual content of a snapshot (see `create_snapshot` function)>
        }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id::text
                 , dataset_id::text
                 , data
                 , created
              FROM dataset_snapshot
             WHERE id = :id
        """), {"id": id})
        row = result.fetchone()
        if not row:
            raise db.exceptions.NoDataFoundException("Can't find dataset snapshot with a specified ID.")
        return dict(row)


def _delete_snapshot(connection, snapshot_id):
    """Delete a snapshot.

    Args:
        connection: an SQLAlchemy connection.
        snapshot_id (string/uuid): ID of a snapshot.
    """
    query = sqlalchemy.text("""
        DELETE FROM dataset_snapshot
              WHERE id = :snapshot_id""")
    connection.execute(query, {"snapshot_id": snapshot_id})


def get_snapshots_for_dataset(dataset_id):
    """Get all snapshots created for a dataset.

    Args:
        dataset_id (string/uuid): ID of a dataset.

    Returns:
        List of snapshots as dictionaries.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id::text
                 , dataset_id::text
                 , data
                 , created
              FROM dataset_snapshot
             WHERE dataset_id = :dataset_id
        """), {"dataset_id": dataset_id})
        return [dict(row) for row in result]


def _delete_snapshots_for_dataset(connection, dataset_id):
    """Delete all snapshots of a dataset.

    Args:
        connection: an SQLAlchemy connection.
        dataset_id (string/uuid): ID of a dataset.
    """
    query = sqlalchemy.text("""
        DELETE FROM dataset_snapshot
              WHERE dataset_id = :dataset_id""")
    connection.execute(query, {"dataset_id": dataset_id})


def _get_classid_for_dataset(connection, dataset_id, class_name):
    query = sqlalchemy.text("""
      SELECT id
        FROM dataset_class
       WHERE name = :name
         AND dataset = :dataset_id""")
    result = connection.execute(query, {"name": class_name, "dataset_id": dataset_id})
    if result.rowcount < 1:
        raise exceptions.NoDataFoundException("No such class exists.")
    clsid = result.fetchone()
    return clsid[0]


def add_recordings(dataset_id, class_name, recordings):
    """Adds new recordings to a class in a dataset.

    If any given recording already exist in this class it is not added again.

    Args:
        dataset_id: the uuid of the dataset
        class_name: The class to add the recordings to
        recordings: List of recordings (MBID strings) to add

    Raises:
        NoDataFoundException if the dataset doesn't exist or if the class doesn't exist in the dataset
    """

    with db.engine.begin() as connection:
        clsid = _get_classid_for_dataset(connection, dataset_id, class_name)
        for mbid in recordings:
            connection.execute(sqlalchemy.text("""
              INSERT INTO dataset_class_member (class, mbid)
                   SELECT :clsid, :mbid
         WHERE NOT EXISTS (SELECT *
                             FROM dataset_class_member d
                            WHERE d.class = :clsid
                              AND d.mbid = :mbid)
                      """),
                               {"clsid": clsid, "mbid": mbid})


def delete_recordings(dataset_id, class_name, recordings):
    """Delete recordings from a dataset class"""

    with db.engine.begin() as connection:
        clsid = _get_classid_for_dataset(connection, dataset_id, class_name)
        for mbid in recordings:
            connection.execute(sqlalchemy.text("""
                DELETE FROM dataset_class_member
                      WHERE class = :class_name
                        AND mbid = :mbid_num
                            """),
                               {"class_name": clsid, "mbid_num": mbid})


def add_class(dataset_id, class_data):
    """Add a class to a dataset

    If the dict argument contains a key "recordings", add these recordings
    to the class as well. See :func:`add_recordings`.
    If the class already exists, do not add it again, but add recordings
    to it if they are given.

    Args:
        dataset_id: the UUID of the dataset to add this class to
        class_data: A dictionary representing the class to add:
              {"name": "Classname", "description": "Class desc",
               "recordings": [list of recording ids (optional)}
    """

    with db.engine.begin() as connection:
        if "description" not in class_data:
            class_data["description"] = ""
        connection.execute(sqlalchemy.text("""
            INSERT INTO dataset_class (name, description, dataset)
                 SELECT :name, :description, :datasetid
       WHERE NOT EXISTS (SELECT *
                           FROM dataset_class d
                          WHERE d.name = :name
                            AND d.dataset = :datasetid)
                    """),
                           {"name": class_data["name"], "description": class_data["description"], "datasetid": dataset_id})
    if "recordings" in class_data:
        add_recordings(dataset_id, class_data["name"], class_data["recordings"])


def delete_class(dataset_id, class_data):
    """Delete a class from a dataset

    Deletes the class members as well since we have ON DELETE CASCADE set in the database

    Args:
        dataset_id: the UUID of the dataset to delete this class from
        class_data: A dictionary representing the class to delete:
              {"name": "Classname"}
    """

    with db.engine.begin() as connection:
        query = sqlalchemy.text("""
            DELETE FROM dataset_class
                  WHERE name = :class_name
                    AND dataset = :dataset_id
                        """)
        connection.execute(query,  {"class_name": class_data["name"], "dataset_id": dataset_id})


def update_class(dataset_id, class_name, class_data):
    """ Update the metadata (name, description) for a class.

    Args:
        dataset_id: id of the dataset to update
        class_name: the name of the class to update
        class_data: dictionary of metadata to update

    Valid keys for `meta` are: `name` (required),
     `new_name` (optional), `description` (optional)
    If one of the optional keys is not present, the corresponding field
    for the class will not be updated. If no keys are present,
    the class will not be updated.
    """

    params = {}
    updates = []
    if "new_name" in class_data:
        updates.append("name = :new_name")
        params["new_name"] = class_data["new_name"]
    if "description" in class_data:
        updates.append("description = :description")
        params["description"] = class_data["description"]
    setstr = ", ".join(updates)
    update_query = text("""UPDATE dataset_class
                               SET %s
                             WHERE id = :id

            """ % setstr)

    if params:
        with db.engine.begin() as connection:
            clsid = _get_classid_for_dataset(connection, dataset_id, class_name)
            params["id"] = clsid

            connection.execute(update_query, params)


def check_recording_in_dataset(dataset_id, mbid):
    """Check whether an MBID is in a given dataset.
    Args:
        dataset_id: ID of a dataset
        mbid: MBID to be checked
    Returns:
        True if an MBID appears anywhere in a dataset, False otherwise
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT dataset_class.id
              FROM dataset_class
              JOIN dataset_class_member
                ON dataset_class_member.class = dataset_class.id
             WHERE dataset_class.dataset = :dataset_id
               AND dataset_class_member.mbid = :mbid
        """), {"dataset_id": dataset_id, "mbid": mbid})

        return result.rowcount > 0
