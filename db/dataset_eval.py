from db import create_cursor, commit
import db.exceptions
import db.dataset
import db.data
import jsonschema

# Job statuses are defined in `eval_job_status` type. See schema definition.
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


def evaluate_dataset(dataset_id):
    """Add dataset into evaluation queue.

    Args:
        dataset_id: ID of the dataset that needs to be added into the list of
            jobs.

    Returns:
        ID of the newly created evaluation job.
    """
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM dataset_eval_jobs WHERE dataset_id = %s AND status IN %s",
            (dataset_id, (STATUS_PENDING, STATUS_RUNNING))
        )
        if cursor.fetchone()[0] > 0:
            raise JobExistsException
    validate_dataset(db.dataset.get(dataset_id))
    return _create_job(dataset_id)


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
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT id, dataset_id, status, status_msg, result, created, updated "
            "FROM dataset_eval_jobs "
            "WHERE status = %s "
            "ORDER BY created ASC "
            "LIMIT 1",
            (STATUS_PENDING,)
        )
        return dict(cursor.fetchone()) if cursor.rowcount > 0 else None


def get_job(job_id):
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT id, dataset_id, status, status_msg, result, created, updated "
            "FROM dataset_eval_jobs "
            "WHERE id = %s",
            (job_id,)
        )
        return dict(cursor.fetchone()) if cursor.rowcount > 0 else None


def get_jobs_for_dataset(dataset_id):
    """Get a list of evaluation jobs for the specified dataset.

    Args:
        dataset_id: UUID of the dataset.

    Returns:
        List of evaluation jobs (dicts) for the dataset. Ordered by creation
        time (oldest job first)
    """
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT id, dataset_id, status, status_msg, result, created, updated "
            "FROM dataset_eval_jobs "
            "WHERE dataset_id = %s "
            "ORDER BY created ASC",
            (dataset_id,)
        )
        return [dict(j) for j in cursor.fetchall()]


def set_job_result(job_id, result):
    with create_cursor() as cursor:
        cursor.execute(
            "UPDATE dataset_eval_jobs "
            "SET (result, updated) = (%s, current_timestamp) "
            "WHERE id = %s",
            (result, job_id)
        )
    commit()


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
    with create_cursor() as cursor:
        cursor.execute(
            "UPDATE dataset_eval_jobs "
            "SET (status, status_msg, updated) = (%s, %s, current_timestamp) "
            "WHERE id = %s",
            (status, status_msg, job_id)
        )
    commit()


def _create_job(dataset_id):
    with create_cursor() as cursor:
        cursor.execute(
            "INSERT INTO dataset_eval_jobs (id, dataset_id, status) "
            "VALUES (uuid_generate_v4(), %s, %s) RETURNING id",
            (dataset_id, STATUS_PENDING)
        )
        job_id = cursor.fetchone()[0]
    commit()
    return job_id


class IncorrectJobStatusException(db.exceptions.DatabaseException):
    pass

class JobExistsException(db.exceptions.DatabaseException):
    """Should be raised when trying to add a job for dataset that already has one."""
    pass

class IncompleteDatasetException(db.exceptions.DatabaseException):
    pass
