import db
import db.exceptions
import db.challenge
import db.dataset
import db.data
import db.user
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
VALID_EVAL_LOCATION = [EVAL_LOCAL, EVAL_REMOTE]

# Filter types are defined in `eval_filter_type` type. See schema definition.
FILTER_ARTIST = "artist"


def evaluate_dataset(dataset_id, normalize, eval_location, filter_type=None, challenge_id=None):
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
        challenge_id: Optional UUID of a challenge. If specified, evaluation
            job will be submitted as a part of that challenge.

    Returns:
        ID of the newly created evaluation job.
    """
    with db.engine.begin() as connection:
        if _job_exists(connection, dataset_id):
            raise JobExistsException
        validate_dataset(db.dataset.get(dataset_id))
        return _create_job(
            connection=connection,
            dataset_id=dataset_id,
            normalize=normalize,
            eval_location=eval_location,
            filter_type=filter_type,
            challenge_id=challenge_id,
        )


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


def get_jobs_in_challenge(challenge_id):
    """Get jobs that were submitted for a specific challenge."""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT dataset_eval_jobs.*
              FROM dataset_eval_challenge
              JOIN dataset_eval_jobs ON dataset_eval_jobs.id = dataset_eval_challenge.dataset_eval_job
             WHERE dataset_eval_challenge.challenge_id = :challenge_id
        """), {"challenge_id": challenge_id})
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


def _create_job(connection, dataset_id, normalize, eval_location, filter_type=None, challenge_id=None):
    if not isinstance(normalize, bool):
        raise ValueError("Argument 'normalize' must be a boolean.")
    if filter_type is not None:
        if filter_type not in [FILTER_ARTIST]:
            raise ValueError("Incorrect 'filter_type'. See module documentation.")
    if eval_location not in VALID_EVAL_LOCATION:
        raise ValueError("Incorrect 'eval_location'. Must be one of %s" % VALID_EVAL_LOCATION)
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
    if challenge_id:
        _submit_for_challenge(
            connection=connection,
            challenge_id=challenge_id,
            dataset_id=dataset_id,
            job_id=job_id,
            snapshot_id=snapshot_id,
        )
    return job_id

def get_remote_pending_jobs_for_user(user_id):
    """ Get all jobs for a user which have been created to
        be evaluated on a remote server.

    Args:
      user_id: the id of the user to get the jobs for
    """

    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
                     SELECT dataset_eval_jobs.id::text,
                            dataset.name,
                            dataset_eval_jobs.created
                       FROM dataset_eval_jobs
                       JOIN dataset_snapshot
                         ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
                       JOIN dataset
                         ON dataset.id = dataset_snapshot.dataset_id
                      WHERE status = :status
                        AND eval_location = :eval_location
                        AND author = :user_id
                   ORDER BY dataset_eval_jobs.created ASC
            """)
        result = connection.execute(query, {
            "status": STATUS_PENDING,
            "eval_location": EVAL_REMOTE,
            "user_id": user_id
        })
        jobs = []
        for row in result.fetchall():
            jobs.append({
                "job_id": row[0],
                "dataset_name": row[1],
                "created": row[2]
                })
        return jobs


def _submit_for_challenge(connection, challenge_id, dataset_id, job_id, snapshot_id):
    """Submit existing dataset for a challenge.

    This function also performs recording filtering (removes recordings that are present in a
    validation dataset from a submission. This is a mandatory step, which updates snapshot that
    was created for evaluation job.
    """
    if not db.challenge.is_ongoing(challenge_id):
        raise db.exceptions.DatabaseException("Can only submit dataset for an ongoing challenge.")
    recordings_to_remove = set()
    validation_snapshot = db.dataset.get_snapshot(db.challenge.get(challenge_id)["validation_snapshot"])["data"]
    for cls in validation_snapshot["classes"]:
        for rec in cls["recordings"]:
            recordings_to_remove.add(rec)
    filtered_ds = _filter_recordings(recordings_to_remove, db.dataset.get(dataset_id))
    db.dataset.replace_snapshot(snapshot_id, filtered_ds)
    db.challenge._submit_eval_job(connection, challenge_id, dataset_id, job_id)


def _filter_recordings(recordings, dataset):
    """This function performs recording filtering in a dataset.

    Args:
        recordings (set): Set of recording IDs (strings) that need to be removed.
        dataset (dict): Dataset to be filtered.

    Returns:
        Dataset with recording filtering applied.
    """
    for cls in dataset["classes"]:
        cls["recordings"] = [r for r in cls["recordings"] if r not in recordings]
    return dataset


class IncompleteDatasetException(db.exceptions.DatabaseException):
    pass

class IncorrectJobStatusException(db.exceptions.DatabaseException):
    pass

class JobNotFoundException(db.exceptions.DatabaseException):
    pass

class JobExistsException(db.exceptions.DatabaseException):
    """Should be raised when trying to add a job for dataset that already has one."""
    pass
