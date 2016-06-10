from hashlib import sha256
from datetime import datetime
import db.dataset
import pytz
from collections import defaultdict
import logging
import copy
import time
import json
import os
import db
import db.exceptions
from sqlalchemy import text
import db
import db.exceptions
import sqlalchemy
import string
import re
import random

KEY_LENGTH = 40


def create(user_id, name, start_time, end_time, classes, validation_dataset_id):
    """Create a new challenge.

    Validation dataset must have the same set of classes as one that is defined for
    a challenge (in `classes` argument).

    Args:
        user_id: User that created a challenge.
        name: Name of a challenge.
        start_time: Time when submissions begin.
        end_time: Time when submissions end.
        classes: List of class names (labels) as strings are required for submissions.
        validation_dataset_id: ID of a dataset that will be used for validation.

    Returns:
        ID of a newly created challenge.
    """
    if end_time < start_time:
        raise ValueError("End time can't be earlier than start time.")
    for cls in classes:
        if not re.match("^[A-Za-z0-9_-]+$", cls):
            raise ValueError("Incorrect class name format.")
    validation_dataset = db.dataset.get(validation_dataset_id)
    _validate_dataset_structure(
        dataset=validation_dataset,
        classes=classes,
    )

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO challenge (id, creator, name, start_time, end_time, classes, validation_snapshot)
                 VALUES (uuid_generate_v4(), :creator, :name, :start_time, :end_time, :classes, :validation_snapshot)
              RETURNING id
        """), {
            "creator": user_id,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "classes": ",".join(set(classes)),
            "validation_snapshot": db.dataset.create_snapshot(validation_dataset["id"]),
        })
        return result.fetchone()["id"]


def _submit_eval_job(connection, challenge_id, dataset_id, job_id):
    _validate_dataset_structure(
        dataset=db.dataset.get(dataset_id),
        classes=get(challenge_id)["classes"],
    )
    connection.execute(sqlalchemy.text("""
        INSERT INTO dataset_eval_challenge (dataset_eval_job, challenge_id)
             VALUES (:dataset_eval_job, :challenge_id)
    """), {
        "dataset_eval_job": job_id,
        "challenge_id": challenge_id,
    })


def _validate_dataset_structure(dataset, classes):
    classes = [c.lower() for c in classes]
    encountered = defaultdict(lambda: False)
    for ds_cls in dataset["classes"]:
        ds_cls_name = ds_cls["name"].lower()
        encountered[ds_cls_name] = True
        if ds_cls_name not in classes:
            raise db.exceptions.BadDataException("Class `%s` defined in the dataset is not a part of required dataset "
                                                 "structure for a challenge. Required classes are: %s." %
                                                 (ds_cls_name, ", ".join(classes)))
    for req_cls in classes:
        if not encountered[req_cls]:
            raise db.exceptions.BadDataException("Dataset is missing a class required by a challenge: %s." % req_cls)


def get(id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, creator, name, start_time, end_time, classes, validation_snapshot, created, concluded
              FROM challenge
             WHERE id = :id
        """), {"id": id})
        row = result.fetchone()
        if not row:
            raise db.exceptions.NoDataFoundException("Can't find challenge with a specified ID.")
        return _prep_full_row_out(row)


def get_submissions(challenge_id, order=None):
    """Get evaluation jobs submitted for a challenge and related information.

    Args:
        challenge_id: ID of a challenge.
        order: Optional sort order of results. Can be one of: `submission`, `accuracy`.
            `submission` - sort by evaluation job creation time.
            `accuracy` - sort by accuracy in a evaluation results (only for completed jobs).
    """
    if order not in ["submission", "accuracy"]:
        raise ValueError("Incorrect order argument.")
    # TODO: Allow to specify offset and limit

    query = """
        SELECT dataset_eval_jobs.id AS job_id,
               dataset_eval_jobs.snapshot_id AS job_snapshot_id,
               dataset_eval_jobs.status AS job_status,
               dataset_eval_jobs.created AS job_created,
               dataset_eval_jobs.result AS job_result,
               dataset.id AS dataset_id,
               dataset.name AS dataset_name,
               dataset.description AS dataset_description,
               dataset.public AS dataset_public,
               dataset.created AS dataset_created,
               dataset.last_edited AS dataset_public,
               "user".id AS user_id,
               "user".musicbrainz_id AS user_musicbrainz_id
          FROM dataset_eval_challenge
          JOIN dataset_eval_jobs ON dataset_eval_jobs.id = dataset_eval_challenge.dataset_eval_job
          JOIN dataset_snapshot ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
          JOIN dataset ON dataset.id = dataset_snapshot.dataset_id
          JOIN "user" ON "user".id = dataset.author
         WHERE dataset_eval_challenge.challenge_id = :challenge_id
    """
    if order == "submission":
        query += "ORDER BY dataset_eval_jobs.created DESC"
    elif order == "accuracy":
        query += "ORDER BY dataset_eval_jobs.result->>'accuracy' DESC"

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), {"challenge_id": challenge_id})
        return [{
            "eval_job": {
                "id": row["job_id"],
                "snapshot_id": row["job_snapshot_id"],
                "status": row["job_status"],
                "created": row["job_created"],
                "job_result": row["job_result"],
                "dataset": {
                    "id": row["dataset_id"],
                    "name": row["dataset_name"],
                    "description": row["dataset_description"],
                    "public": row["dataset_public"],
                    "created": row["dataset_created"],
                    "author": {
                        "id": row["user_id"],
                        "musicbrainz_id": row["user_musicbrainz_id"],
                    },
                },
            },
        } for row in result.fetchall()]


def find_active(query):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, creator, name, start_time, end_time, created, classes
              FROM challenge
             WHERE name ILIKE :query_like
        """), {
            "query_like": '%' + query + '%',
        })
        return [_prep_full_row_out(row) for row in result.fetchall()]


def list_all(content_filter=None, limit=20, offset=0):
    with db.engine.connect() as connection:

        if not content_filter or content_filter == "all":
            result = connection.execute(sqlalchemy.text("""
                SELECT id, creator, name, start_time, end_time, created, concluded, classes
                  FROM challenge
              ORDER BY start_time DESC, end_time DESC
                 LIMIT :limit
                OFFSET :offset
            """), {
                "limit": limit,
                "offset": offset,
            })
            result_count = connection.execute("SELECT COUNT(*) FROM challenge")

        elif content_filter == "upcoming":
            result = connection.execute(sqlalchemy.text("""
                SELECT id, creator, name, start_time, end_time, created, concluded, classes
                  FROM challenge
                 WHERE start_time > :now
              ORDER BY start_time DESC, end_time DESC
                 LIMIT :limit
                OFFSET :offset
            """), {
                "now": datetime.now(pytz.utc),
                "limit": limit,
                "offset": offset,
            })
            result_count = connection.execute(sqlalchemy.text("""
                SELECT COUNT(*)
                  FROM challenge
                 WHERE start_time > :now
            """), {"now": datetime.now(pytz.utc)})

        elif content_filter == "active":
            result = connection.execute(sqlalchemy.text("""
                SELECT id, creator, name, start_time, end_time, created, concluded, classes
                  FROM challenge
                 WHERE start_time < :now AND end_time > :now
              ORDER BY start_time DESC, end_time DESC
                 LIMIT :limit
                OFFSET :offset
            """), {
                "now": datetime.now(pytz.utc),
                "limit": limit,
                "offset": offset,
            })
            result_count = connection.execute(sqlalchemy.text("""
                SELECT COUNT(*)
                  FROM challenge
                 WHERE start_time < :now AND end_time > :now
            """), {"now": datetime.now(pytz.utc)})

        elif content_filter == "ended":
            result = connection.execute(sqlalchemy.text("""
                SELECT id, creator, name, start_time, end_time, created, concluded, classes
                  FROM challenge
                 WHERE end_time < :now
              ORDER BY start_time DESC, end_time DESC
                 LIMIT :limit
                OFFSET :offset
            """), {
                "now": datetime.now(pytz.utc),
                "limit": limit,
                "offset": offset,
            })
            result_count = connection.execute(sqlalchemy.text("""
                SELECT COUNT(*)
                  FROM challenge
                 WHERE end_time < :now
            """), {"now": datetime.now(pytz.utc)})

        else:
            raise db.exceptions.DatabaseException("Incorrect content filter: %s. Must be one of %s." %
                                                  (content_filter, ["all", "upcoming", "active", "ended"]))

        return [_prep_full_row_out(row) for row in result.fetchall()], result_count.fetchone()[0]


def update(id, name, start_time, end_time):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE challenge
               SET name = :name, start_time = :start_time, end_time = :end_time
             WHERE id = :id
        """), {
            "id": id,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
        })


def delete(id):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM challenge
             WHERE id = :id
        """), {"id": id})


def _prep_full_row_out(row):
    row = dict(row)
    row["classes"] = row["classes"].split(",")
    return row
