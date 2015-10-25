import db
import db.exceptions
import db.dataset
import db.data
import json
import jsonschema
import sqlalchemy
from sqlalchemy import text


# Job statuses are defined in `eval_job_status` type. See schema definition.
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

# Filter types are defined in `eval_filter_type` type. See schema definition.
FILTER_ARTIST = "artist"


def evaluate_dataset(dataset_id, normalize, filter_type=None):
    """Add dataset into evaluation queue.

    Args:
        dataset_id: ID of the dataset that needs to be added into the list of
            jobs.
        normalize: Dataset will be "randomly" normalized if set to True.
            Normalization is reducing each class to have the same number of
            recordings.
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
        return _create_job(connection, dataset_id, normalize, filter_type)


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
    result = connection.execute(
        "SELECT count(*) FROM dataset_eval_jobs WHERE dataset_id = %s AND status IN %s",
        (dataset_id, (STATUS_PENDING, STATUS_RUNNING))
    )
    return result.fetchone()[0] > 0


def validate_dataset(dataset):
    """Validate dataset by making sure that it matches JSON Schema for complete
    datasets (JSON_SCHEMA_COMPLETE) and checking if all recordings referenced
    in classes have low-level information in the database.

    Raises IncompleteDatasetException if dataset is not ready for evaluation.
    """
    try:
        jsonschema.validate(dataset, db.dataset.JSON_SCHEMA_COMPLETE)
    except jsonschema.ValidationError as e:
        raise IncompleteDatasetException(e)

    rec_memo = {}
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            if recording_mbid in rec_memo and rec_memo[recording_mbid]:
                pass
            if db.data.count_lowlevel(recording_mbid) > 0:
                rec_memo[recording_mbid] = True
            else:
                raise IncompleteDatasetException(
                    "Can't find low-level data for recording: %s" % recording_mbid)


def get_next_pending_job():
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT id::text, dataset_id::text, status, status_msg, result, options, created, updated "
            "FROM dataset_eval_jobs "
            "WHERE status = %s "
            "ORDER BY created ASC "
            "LIMIT 1",
            (STATUS_PENDING,)
        )
        row = result.fetchone()
        return dict(row) if row else None


def get_job(job_id):
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT id, dataset_id, status, status_msg, result, options, created, updated "
            "FROM dataset_eval_jobs "
            "WHERE id = %s",
            (job_id,)
        )
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
        result = connection.execute(
            "SELECT id, dataset_id, status, status_msg, result, options, created, updated "
            "FROM dataset_eval_jobs "
            "WHERE dataset_id = %s "
            "ORDER BY created ASC",
            (dataset_id,)
        )
        return [dict(j) for j in result.fetchall()]


def set_job_result(job_id, result):
    with db.engine.begin() as connection:
        connection.execute(
            "UPDATE dataset_eval_jobs "
            "SET (result, updated) = (%s, current_timestamp) "
            "WHERE id = %s",
            (result, job_id)
        )

def add_datasets_to_job(job_id, training, testing):
    """Add a training and testing set to a job

    Args:
        job_id: ID of the job to add the datasets to
        training: Dictionary of the training set for the job
        testing : Dictionary of the test set
    """
    with db.engine.begin() as connection:
        training_id = add_dataset_snapshot(connection, training)
        testing_id = add_dataset_snapshot(connection, testing)
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


def get_dataset_snapshot(id):
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT id, data "
            "FROM dataset_snapshot "
            "WHERE id = %s",
            (id,)
        )
        row = result.fetchone()
        return dict(row) if row else None


def add_dataset_snapshot(connection, data):
    query = text(
        """INSERT INTO dataset_snapshot (data)
        VALUES (:data)
        RETURNING id""")
    result = connection.execute(query, {"data": json.dumps(data)})
    snapshot_id = result.fetchone()[0]
    return snapshot_id


def _create_job(connection, dataset_id, normalize, filter_type=None):
    if not isinstance(normalize, bool):
        raise ValueError("Argument 'normalize' must be a boolean.")
    if filter_type is not None:
        if filter_type not in [FILTER_ARTIST]:
            raise ValueError("Incorrect 'filter_type'. See module documentation.")
    query = sqlalchemy.text("""
                INSERT INTO dataset_eval_jobs (id, dataset_id, status, options)
                     VALUES (uuid_generate_v4(), :dataset_id, :status, :options)
                  RETURNING id
            """)
    result = connection.execute(query, {
        "dataset_id": dataset_id,
        "status": STATUS_PENDING,
        "options": json.dumps({
            "normalize": normalize,
            "filter_type": filter_type,
        }),
    })
    job_id = result.fetchone()[0]
    return job_id


class IncorrectJobStatusException(db.exceptions.DatabaseException):
    pass

class JobExistsException(db.exceptions.DatabaseException):
    """Should be raised when trying to add a job for dataset that already has one."""
    pass

class IncompleteDatasetException(db.exceptions.DatabaseException):
    pass
