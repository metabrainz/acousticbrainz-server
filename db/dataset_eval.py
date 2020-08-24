import db
import db.exceptions
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

# Columns to select when getting a job
EVAL_COLUMNS = ["dataset_eval_jobs.id::text",
                "dataset_snapshot.dataset_id::text",
                "dataset_eval_jobs.snapshot_id::text",
                "dataset_eval_jobs.status",
                "dataset_eval_jobs.status_msg", 
                "dataset_eval_jobs.result", 
                "dataset_eval_jobs.options", 
                "dataset_eval_jobs.training_snapshot", 
                "dataset_eval_jobs.testing_snapshot", 
                "dataset_eval_jobs.created", 
                "dataset_eval_jobs.updated", 
                "dataset_eval_jobs.eval_location"]
EVAL_COLUMNS_COMMA_SEPARATED = ", ".join(EVAL_COLUMNS)

VALID_STATUSES = [STATUS_PENDING, STATUS_RUNNING, STATUS_DONE, STATUS_FAILED]

# Location to run an evaluation (on the AB server of the user's local server),
# defined in postgres type 'eval_location_type'
EVAL_LOCAL = "local"
EVAL_REMOTE = "remote"
VALID_EVAL_LOCATION = [EVAL_LOCAL, EVAL_REMOTE]

# Filter types are defined in `eval_filter_type` type. See schema definition.
FILTER_ARTIST = "artist"

# Default values for parameters
DEFAULT_PARAMETER_PREPROCESSING = ['basic', 'lowlevel', 'nobands', 'normalized', 'gaussianized']
DEFAULT_PARAMETER_C = [-5, -3, -1, 1, 3, 5, 7, 9, 11]
DEFAULT_PARAMETER_GAMMA = [3, 1, -1, -3, -5, -7, -9, -11]


def evaluate_dataset(dataset_id, normalize, eval_location, c_values=None, gamma_values=None,
                     preprocessing_values=None, filter_type=None):
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
        c_values (optional): A list of numerical values to use as the C parameter to the SVM model.
            If not set, use DEFAULT_PARAMETER_C
        gamma_values (optional): A list of numerical values to be used as the gamma parameter
            to the SVM model. If not set, use DEFAULT_PARAMETER_GAMMA
        preprocessing_values (optional): A list of preprocessing steps to be performed in the
            model grid search. If not set, use DEFAULT_PARAMETER_PREPROCESSING
        filter_type: Optional filtering that will be applied to the dataset.
            See FILTER_* variables in this module for a list of existing
            filters.

    Raises:
        JobExistsException: if the dataset has already been submitted for evaluation
        IncompleteDatasetException: if the dataset is incomplete (it has recordings that aren't in AB)

    Returns:
        ID of the newly created evaluation job.
    """

    if c_values is None:
        c_values = DEFAULT_PARAMETER_C
    if gamma_values is None:
        gamma_values = DEFAULT_PARAMETER_GAMMA
    if preprocessing_values is None:
        preprocessing_values = DEFAULT_PARAMETER_PREPROCESSING

    with db.engine.begin() as connection:
        if _job_exists(connection, dataset_id):
            raise JobExistsException

        # Validate dataset contents
        validate_dataset_contents(db.dataset.get(dataset_id))
        return _create_job(connection, dataset_id, normalize, eval_location,
                           c_values, gamma_values, preprocessing_values, filter_type)


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
         WHERE dataset_snapshot.dataset_id = :dataset_id AND dataset_eval_jobs.status IN :statuses
    """), {
        "dataset_id": dataset_id,
        "statuses": (STATUS_PENDING, STATUS_RUNNING),
    })
    return result.fetchone()[0] > 0


def validate_dataset_structure(dataset):
    """Validate dataset structure by making sure that it has at
    least two classes and two recordings in each class.

    Raises IncompleteDatasetException if dataset doesn't satisfy the
    structure needs for evaluation.
    """
    MIN_CLASSES = 2
    MIN_RECORDINGS_IN_CLASS = 2

    if len(dataset["classes"]) < MIN_CLASSES:
        raise IncompleteDatasetException(
            "Dataset needs to have at least %s classes." % MIN_CLASSES
        )
    for cls in dataset["classes"]:
        if len(cls["recordings"]) < MIN_RECORDINGS_IN_CLASS:
            raise IncompleteDatasetException(
                "There are not enough recordings in a class `%s` (%s). "
                "At least %s are required in each class." %
                (cls["name"], len(cls["recordings"]), MIN_RECORDINGS_IN_CLASS)
            )


def validate_dataset_contents(dataset):
    """Validate dataset contents by checking if all recordings referenced
    in classes have low-level information in the database.

    Raises IncompleteDatasetException if contents of the dataset are not
    found.
    """
    rec_memo = {}

    for cls in dataset["classes"]:
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
    """
    Get the earliest submitted job which is still in the pending state.

    Returns:
         The next job to process
    """
    with db.engine.connect() as connection:
        query = text(
            """SELECT %s
                 FROM dataset_eval_jobs
                 JOIN dataset_snapshot 
                   ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
                WHERE status = :status
                  AND eval_location = 'local'
             ORDER BY created ASC
                LIMIT 1
            """ % EVAL_COLUMNS_COMMA_SEPARATED)
        result = connection.execute(query, {"status": STATUS_PENDING})
        row = result.fetchone()
        return dict(row) if row else None


def get_job(job_id):
    """
    Get an evaluation job.

    Arguments:
        job_id: the id to the job to retrieve

    Returns:
        The evaluation job with the specified id
    """
    with db.engine.connect() as connection:
        query = text(
            """SELECT %s
                 FROM dataset_eval_jobs
                 JOIN dataset_snapshot ON dataset_snapshot.id = dataset_eval_jobs.snapshot_id
                WHERE dataset_eval_jobs.id = :id""" % EVAL_COLUMNS_COMMA_SEPARATED)
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


def _create_job(connection, dataset_id, normalize, eval_location, c_value,
                gamma_value, preprocessing_values, filter_type):
    if not isinstance(normalize, bool):
        raise ValueError("Argument 'normalize' must be a boolean.")
    if filter_type is not None:
        if filter_type not in [FILTER_ARTIST]:
            raise ValueError("Incorrect 'filter_type'. See module documentation.")
    if eval_location not in VALID_EVAL_LOCATION:
        raise ValueError("Incorrect 'eval_location'. Must be one of %s" % VALID_EVAL_LOCATION)

    options = {
            "normalize": normalize,
            "filter_type": filter_type,
            "c_values": c_value,
            "gamma_values": gamma_value,
            "preprocessing_values": preprocessing_values,
        }

    snapshot_id = db.dataset.create_snapshot(dataset_id)
    query = sqlalchemy.text("""
                INSERT INTO dataset_eval_jobs (id, snapshot_id, status, options, eval_location)
                     VALUES (uuid_generate_v4(), :snapshot_id, :status, :options, :eval_location)
                  RETURNING id
            """)
    result = connection.execute(query, {
        "snapshot_id": snapshot_id,
        "status": STATUS_PENDING,
        "options": json.dumps(options),
        "eval_location": eval_location
    })
    job_id = result.fetchone()[0]
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


class IncompleteDatasetException(db.exceptions.DatabaseException):
    pass


class IncorrectJobStatusException(db.exceptions.DatabaseException):
    pass


class JobNotFoundException(db.exceptions.DatabaseException):
    pass


class JobExistsException(db.exceptions.DatabaseException):
    """Should be raised when trying to add a job for dataset that already has one."""
    pass
