import db
import db.exceptions
import db.dataset
import db.data
import json
import sqlalchemy
from sqlalchemy import text

# Job statuses are defined in `eval_job_status` type. See schema definition.
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

VALID_STATUSES = [STATUS_PENDING, STATUS_RUNNING, STATUS_DONE, STATUS_FAILED]

# Location to run an evaluation (on the AB server of the user's local server),
# defined in postgres type 'eval_location_type'
EVAL_LOCAL = "local"
EVAL_REMOTE = "remote"

# Filter types are defined in `eval_filter_type` type. See schema definition.
FILTER_ARTIST = "artist"


def evaluate_dataset(dataset_id, normalize, eval_location, filter_type=None):
    """Add dataset into evaluation queue.

    Args:
        dataset_id: ID of the dataset that needs to be added into the list of
            jobs.
        normalize: Dataset will be "randomly" normalized if set to True.
            Normalization is reducing each class to have the same number of
            recordings.
        eval_location: The user should choose to evaluate on his own machine
            or on the AB server. 'local' is for AB server and 'remote' is for
            user's machine.
        filter_type: Optional filtering that will be applied to the dataset.
            See FILTER_* variables in this module for a list of existing
            filters.

    Returns:
        ID of the newly created evaluation job.
    """
    with db.engine.begin() as connection:
        if _job_exists(connection, dataset_id):
            raise JobExistsException
        validate_dataset(db.dataset.get(dataset_id))
        return _create_job(connection, dataset_id, normalize, eval_location, filter_type)


def job_exists(dataset_id):
    """Checks if there's already a pending or running job for this dataset in a
    queue.

    Args:
        dataset_id: ID of the dataset which needs to be checked.

    Returns:
        True if there's a pending or running job, False otherwise.
    """
    with db.engine.begin() as connection:
        return _job_exists(connection, dataset_id)


def _job_exists(connection, dataset_id):
    result = connection.execute(sqlalchemy.text("""
        SELECT count(*)
          FROM dataset_eval_jobs
          JOIN dataset_snapshot ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
         WHERE dataset_snapshot.dataset_id = :dataset_id AND dataset_eval_jobs.status IN :statses
    """), {
        "dataset_id": dataset_id,
        "statses": (STATUS_PENDING, STATUS_RUNNING),
    })
    return result.fetchone()[0] > 0


def validate_dataset(dataset):
    """Validate dataset by making sure that it's complete and checking if all
    recordings referenced in classes have low-level information in the database.

    Raises IncompleteDatasetException if dataset is not ready for evaluation.
    """
    MIN_CLASSES = 2
    MIN_RECORDINGS_IN_CLASS = 2

    rec_memo = {}

    if len(dataset["classes"]) < MIN_CLASSES:
        raise IncompleteDatasetException(
            "Dataset needs to have at least %s classes." % MIN_CLASSES
        )
    for cls in dataset["classes"]:
        if len(cls["recordings"]) < MIN_RECORDINGS_IN_CLASS:
            # TODO: Would be nice to mention class name in an error message.
            raise IncompleteDatasetException(
                "There are not enough recordings in a class `%s` (%s). "
                "At least %s are required in each class." %
                (cls["name"], len(cls["recordings"]), MIN_RECORDINGS_IN_CLASS)
            )
        for recording_mbid in cls["recordings"]:
            if recording_mbid in rec_memo and rec_memo[recording_mbid]:
                pass
            if db.data.count_lowlevel(recording_mbid) > 0:
                rec_memo[recording_mbid] = True
            else:
                raise IncompleteDatasetException(
                    "Can't find low-level data for recording: %s" % recording_mbid
                )


def get_next_pending_job():
    # TODO: This should return the same data as `get_job`, so
    #       we run 2 queries, however it would be more efficient
    #       to do it in 1 query
    with db.engine.connect() as connection:
        query = text(
            """SELECT id::text
                 FROM dataset_eval_jobs
                WHERE status = :status
                  AND eval_location = 'local'
             ORDER BY created ASC
                LIMIT 1""")
        result = connection.execute(query, {"status": STATUS_PENDING})
        row = result.fetchone()
        return get_job(row[0]) if row else None


def get_job(job_id):
    with db.engine.connect() as connection:
        query = text(
            """SELECT dataset_eval_jobs.id::text
                    , dataset_snapshot.dataset_id::text
                    , dataset_eval_jobs.snapshot_id::text
                    , dataset_eval_jobs.status
                    , dataset_eval_jobs.status_msg
                    , dataset_eval_jobs.result
                    , dataset_eval_jobs.options
                    , dataset_eval_jobs.training_snapshot
                    , dataset_eval_jobs.testing_snapshot
                    , dataset_eval_jobs.created
                    , dataset_eval_jobs.updated
                    , dataset_eval_jobs.eval_location
                 FROM dataset_eval_jobs
                 JOIN dataset_snapshot ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
                WHERE dataset_eval_jobs.id = :id""")
        result = connection.execute(query, {"id": job_id})

        row = result.fetchone()
        return dict(row) if row else None


def get_jobs_for_dataset(dataset_id):
    """Get a list of evaluation jobs for the specified dataset.

    Args:
        dataset_id: UUID of the dataset.

    Returns:
        List of evaluation jobs (dicts) for the dataset. Ordered by creation
        time (oldest job first)
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT dataset_eval_jobs.*
              FROM dataset_eval_jobs
              JOIN dataset_snapshot ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
             WHERE dataset_snapshot.dataset_id = :dataset_id
          ORDER BY dataset_eval_jobs.created ASC
        """), {"dataset_id": dataset_id})
        return [dict(j) for j in result.fetchall()]


def set_job_result(job_id, result):
    with db.engine.begin() as connection:
        connection.execute(
            "UPDATE dataset_eval_jobs "
            "SET (result, updated) = (%s, current_timestamp) "
            "WHERE id = %s",
            (result, job_id)
        )


def add_sets_to_job(job_id, training, testing):
    """Add a training and testing set to a job

    Args:
        job_id: ID of the job to add the datasets to
        training: Dictionary of the training set for the job
        testing : Dictionary of the test set
    """
    with db.engine.begin() as connection:
        training_id = add_dataset_eval_set(connection, training)
        testing_id = add_dataset_eval_set(connection, testing)
        query = text(
            """UPDATE dataset_eval_jobs
                  SET (training_snapshot, testing_snapshot) = (:training_id, :testing_id)
                WHERE id = :job_id""")
        connection.execute(query, {"training_id": training_id,
                                   "testing_id": testing_id,
                                   "job_id": job_id})


def set_job_status(job_id, status, status_msg=None):
    """Set status for existing job.

    Args:
        job_id: ID of the job that needs a status update.
        status: One of statuses: STATUS_PENDING, STATUS_RUNNING, STATUS_DONE,
            or STATUS_FAILED.
        status_msg: Optional status message that can be used to provide
            additional information about status that is being set. For example,
            error message if it's STATUS_FAILED.
    """
    if status not in [STATUS_PENDING,
                      STATUS_RUNNING,
                      STATUS_DONE,
                      STATUS_FAILED]:
        raise IncorrectJobStatusException
    with db.engine.begin() as connection:
        connection.execute(
            "UPDATE dataset_eval_jobs "
            "SET (status, status_msg, updated) = (%s, %s, current_timestamp) "
            "WHERE id = %s",
            (status, status_msg, job_id)
        )


def delete_job(job_id):
    with db.engine.begin() as connection:
        result = connection.execute("""
            SELECT snapshot_id::text
                 , status
              FROM dataset_eval_jobs
             WHERE id = %s
        """, (job_id,))
        row = result.fetchone()
        if not row:
            raise JobNotFoundException("Can't find evaluation job with a specified ID.")
        status = row["status"]
        if status != STATUS_PENDING:
            raise db.exceptions.DatabaseException("Cannot delete this evaluation job because it's not in the queue."
                                                  " Current status: %s." % status)
        connection.execute(
            "DELETE FROM dataset_eval_jobs WHERE id = %s",
            (job_id,)
        )
        db.dataset._delete_snapshot(connection, row["snapshot_id"])


def get_dataset_eval_set(id):
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT id, data "
            "FROM dataset_eval_sets "
            "WHERE id = %s",
            (id,)
        )
        row = result.fetchone()
        return dict(row) if row else None


def add_dataset_eval_set(connection, data):
    query = text(
        """INSERT INTO dataset_eval_sets (data)
        VALUES (:data)
        RETURNING id""")
    result = connection.execute(query, {"data": json.dumps(data)})
    snapshot_id = result.fetchone()[0]
    return snapshot_id


def _create_job(connection, dataset_id, normalize, eval_location, filter_type=None):
    if not isinstance(normalize, bool):
        raise ValueError("Argument 'normalize' must be a boolean.")
    if filter_type is not None:
        if filter_type not in [FILTER_ARTIST]:
            raise ValueError("Incorrect 'filter_type'. See module documentation.")
    snapshot_id = db.dataset.create_snapshot(dataset_id)
    query = sqlalchemy.text("""
                INSERT INTO dataset_eval_jobs (id, snapshot_id, status, options, eval_location)
                     VALUES (uuid_generate_v4(), :snapshot_id, :status, :options, :eval_location)
                  RETURNING id
            """)
    result = connection.execute(query, {
        "snapshot_id": snapshot_id,
        "status": STATUS_PENDING,
        "options": json.dumps({
            "normalize": normalize,
            "filter_type": filter_type,
        }),
        "eval_location": eval_location
    })
    job_id = result.fetchone()[0]
    return job_id


def get_user_pending_jobs(user_api_key):
    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
                    SELECT dataset_eval_jobs.id
                    FROM   dataset_eval_jobs, dataset_snapshot, dataset, api_key
                    WHERE  dataset.id = dataset_snapshot.dataset_id
                    AND    dataset_snapshot.id = dataset_eval_jobs.snapshot_id
                    AND    api_key.value = :author_api_key
                    AND    status = :status
                    AND    eval_location = :eval_location
                    AND    author = api_key.owner
                    ORDER BY dataset_eval_jobs.created ASC
                """)
        result = connection.execute(query, {
        "status": STATUS_PENDING,
        "eval_location": EVAL_REMOTE,
        "author_api_key": user_api_key
        })
        job_ids = result.fetchall()
        return job_ids


class IncompleteDatasetException(db.exceptions.DatabaseException):
    pass

class IncorrectJobStatusException(db.exceptions.DatabaseException):
    pass

class JobNotFoundException(db.exceptions.DatabaseException):
    pass

class JobExistsException(db.exceptions.DatabaseException):
    """Should be raised when trying to add a job for dataset that already has one."""
    pass
