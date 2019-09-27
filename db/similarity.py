from __future__ import absolute_import
from flask import current_app

import db
from db.data import count_all_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
import similarity.metrics
import similarity.utils

from sqlalchemy import text
from collections import defaultdict

PROCESS_BATCH_SIZE = 10000

def add_index(metric, batch_size=None, n_trees=10, distance_type='angular'):
    """Creates an annoy index for the specified metric, adds all items to the index."""
    current_app.logger.info("Initializing index...")
    index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type)

    batch_size = batch_size or PROCESS_BATCH_SIZE
    offset = 0
    count = 0

    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT MAX(id)
              FROM similarity.similarity
        """)
        total = result.fetchone()[0]

        batch_query = text("""
            SELECT *
              FROM similarity.similarity
             ORDER BY id
             LIMIT :batch_size
            OFFSET :offset
        """)

        current_app.logger.info("Inserting items...")
        while True:
            # Get ids and vectors for specific metric in batches
            batch_result = connection.execute(batch_query, { "batch_size": batch_size, "offset": offset })
            if not batch_result.rowcount:
                current_app.logger.info("Finished adding items. Building index...")
                break

            for row in batch_result.fetchall():
                while not row["id"] == count:
                    # Rows are empty, add zero vector
                    placeholder = [0] * index.dimension
                    index.add_recording_with_vector(count, placeholder)
                    count += 1
                index.add_recording_with_vector(row["id"], row[index.metric_name])
                count += 1

            offset += batch_size
            current_app.logger.info("Items added: {}/{} ({:.3f}%)".format(offset, total, float(offset) / total * 100))

        index.build()
        current_app.logger.info("Saving index...")
        index.save()


def get_all_metrics():
    with db.engine.begin() as connection:
        result = connection.execute("""
            SELECT category, metric, description
            FROM similarity.similarity_metrics
        """)

        metrics = {}
        for category, metric, description in result.fetchall():
            if category not in metrics:
                metrics[category] = []
            metrics[category].append([metric, description])

        return metrics


def add_indices(indices, batch_size):
    offset = 0
    count = 0
    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT MAX(id)
              FROM similarity.similarity
        """)
        total = result.fetchone()[0]

        batch_query = text("""
            SELECT *
              FROM similarity.similarity
             ORDER BY id
             LIMIT :batch_size
            OFFSET :offset
        """)

        while True:
            # Get ids and vectors for all metrics in batches
            batch_result = connection.execute(batch_query, { "batch_size": batch_size, "offset": offset })
            if not batch_result.rowcount:
                current_app.logger.info("Finished adding items. Building and saving indices...")
                break

            for row in batch_result.fetchall():
                while not row["id"] == count:
                    # Rows are empty, add zero vector
                    for index in indices:
                        placeholder = [0] * index.dimension
                        index.add_recording_with_vector(count, placeholder)
                    count += 1
                for index in indices:
                    index.add_recording_with_vector(row["id"], row[index.metric_name])
                count += 1

            offset += batch_size
            current_app.logger.info("Items added: {}/{} ({:.3f}%)".format(offset, total, float(offset) / total * 100))

        for index in indices:
            index.build()
            index.save()


def get_all_metrics():
    """Returns: a dictionary of all existing metrics, of the form:
            {"category": [(metric_name, metric_description)]}
    """
    with db.engine.connect() as connection:
        query = text("""
            SELECT category
                 , metric
                 , description
              FROM similarity.similarity_metrics
        """)
        result = connection.execute(query)

        metrics = {}
        for category, metric, description in result.fetchall():
            if category not in metrics:
                metrics[category] = []
            metrics[category].append([metric, description])

        return metrics


def get_metric_info(metric):
    """Returns metric info as a list in the form:
            [category, metric_name, metric_description]

    If no metric is available, a NoDataFoundException will
    be raised.
    """
    with db.engine.connect() as connection:
        query = text("""
            SELECT category
                 , metric
                 , description
              FROM similarity.similarity_metrics
             WHERE metric = :metric
        """)
        result = connection.execute(query, {"metric": metric})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException("There is no existing metric for the `metric` parameter.")
        return result.fetchone()


def add_metrics(batch_size=None):
    batch_size = batch_size or PROCESS_BATCH_SIZE
    lowlevel_count = count_all_lowlevel()

    with db.engine.connect() as connection:
        metrics = similarity.utils.init_metrics()

        # Collect and assign stats to metrics that require normalization
        for metric in metrics:
            db.similarity_stats.assign_stats(metric)

        sim_count = count_similarity()
        current_app.logger.info("Processed {} / {} ({:.3f}%)".format(sim_count,
                                                            lowlevel_count,
                                                            float(sim_count) / lowlevel_count * 100))

        while True:
            with connection.begin():
                result = get_batch_data(connection, batch_size)
                if not result:
                    break
                for row in result:
                    data = (row["ll_data"], row["hl_data"])
                    submit_similarity_by_id(row["id"], data=data, metrics=metrics, connection=connection)

            sim_count = count_similarity()
            current_app.logger.info("Processed {} / {} ({:.3f}%)".format(sim_count,
                                                                lowlevel_count,
                                                                float(sim_count) / lowlevel_count * 100))


def get_batch_data(connection, batch_size):
    """Performs a query to collect highlevel models and lowlevel
    data for a batch of `batch_size` recordings.

    Args:
        connection: a connection to the database.
        batch_size: the number of recordings (rows) that should
        be collected in the query.
    
    Returns:
        If no rows are returned by the query, i.e. there are no
        available submissions, then None is returned.

        Otherwise, the result object of the query is returned.
    """
    batch_query = text("""
          WITH ll AS (
        SELECT id
          FROM lowlevel ll
         WHERE NOT EXISTS (
               SELECT id
               FROM similarity.similarity AS s
               WHERE s.id = ll.id)
         LIMIT :batch_size
        ),
               hlm AS (
        SELECT highlevel
             , COALESCE(jsonb_object_agg(model.model, hlm.data)
               FILTER (
               WHERE model.model IS NOT NULL
               AND hlm.data IS NOT NULL), NULL)::jsonb AS data
          FROM highlevel_model AS hlm
          JOIN model
            ON model.id = hlm.model
         WHERE highlevel IN (
               SELECT id
               FROM ll)
      GROUP BY (highlevel)
        ),
               llj AS (
        SELECT id
             , data
          FROM lowlevel_json
         WHERE id IN (
               SELECT id
               FROM ll)
        )
        SELECT ll.id AS id
             , llj.data AS ll_data
             , hlm.data AS hl_data
          FROM ll
          JOIN llj
         USING (id)
     LEFT JOIN hlm
            ON hlm.highlevel = ll.id
    """)

    result = connection.execute(batch_query, {"batch_size": batch_size})
    if not result.rowcount:
        return None
    return result


def insert_similarity(connection, id, vectors, metric_names):
    """Inserts a row of similarity vectors for a given lowlevel.id into
    the similarity table.

        Args:
            connection: a connection to the database.
            id: lowlevel.id to be submitted.
            vectors: list of metric vectors for a recording.
            metric_names: corresponding list of metric names.
    """
    params = {}
    params["id"] = id
    for name, vector in zip(metric_names, vectors):
        params[name] = list(vector)

    query = text("""
        INSERT INTO similarity.similarity (
                    id, %(names)s)
             VALUES ( 
                    :id, %(values)s)
        ON CONFLICT (id)
         DO NOTHING
    """ % {"names": ', '.join(metric_names),
           "values": ':' + ', :'.join(metric_names)})
    connection.execute(query, params)


def count_similarity():
    # Get total number of submissions in similarity table
    with db.engine.connect() as connection:
        query = text("""
            SELECT COUNT(*)
              FROM similarity.similarity
        """)
        result = connection.execute(query)
        return result.fetchone()[0]


def submit_similarity_by_id(id, data=None, metrics=None, connection=None):
    """Computes similarity metrics for a single recording specified
    by lowlevel.id, then inserts the metrics as a new row in the
    similarity table.
    
    Args:
        id: lowlevel.id for desired submission.
        
        data: a list (lowlevel_data, highlevel_models). Defaults to None,
        in which case the data will be collected before submission.
        
        metrics: a list of initialized metric classes, for which similarity
        vectors should be computed and submitted. Default is None, in which
        case base metrics will be initialized.

        connection: a connection to the database can be specified if this
        submission should be part of an ongoing transaction.
    """
    try:
        id = int(id)
    except ValueError:
        raise BadDataException('Parameter `id` must be an integer.')

    if not metrics:
        metrics = similarity.utils.init_metrics()
        # Collect and assign stats to metrics that require normalization
        for metric in metrics:
            db.similarity_stats.assign_stats(metric)

    if not data:
        # When a single recording is submitted, not in batch submission,
        # data can be computed here.
        ll_data = db.data.get_lowlevel_by_id(id)
        models = db.data.get_highlevel_models(id)
        data = (ll_data, models)

    vectors = []
    metric_names = []
    for metric in metrics:
        try:
            metric_data = metric.get_feature_data(data[0])
        except AttributeError:
            # High level metrics use models for transformation.
            metric_data = data[1]

        try:
            vector = metric.transform(metric_data)
        except ValueError:
            vector = [0] * metric.length()
        vectors.append(vector)
        metric_names.append(metric.name)

    if connection:
        insert_similarity(connection, id, vectors, metric_names)
    else:
        with db.engine.connect() as connection:
            insert_similarity(connection, id, vectors, metric_names)


def submit_similarity_by_mbid(mbid, offset):
    """Computes similarity metrics for a single recording specified
    by (mbid, offset) combination, then inserts the metrics as a new
    row in the similarity table."""
    id = db.data.get_lowlevel_id(mbid, offset)
    submit_similarity_by_id(id)


def get_metric_dimension(metric_name):
    # Get dimension of vectors for a metric in similarity table
    if metric_name not in similarity.metrics.BASE_METRICS:
        raise db.exceptions.NoDataFoundException("No existing metric named \"{}\"".format(metric_name))
    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT *
              FROM similarity.similarity
             LIMIT 1
        """)
        try:
            dimension = len(result.fetchone()[metric_name])
            return dimension
        except TypeError:
            raise db.exceptions.NoDataFoundException("No existing similarity data.")


def get_similarity_row_mbid(mbid, offset):
    # Get a single row of the similarity table by (MBID, offset) combination
    with db.engine.connect() as connection:
        query = text("""
            SELECT *
              FROM similarity.similarity
             WHERE id = (
                SELECT id
                  FROM lowlevel
                 WHERE gid = :mbid
                   AND submission_offset = :offset )
        """)
        result = connection.execute(query, {"mbid": mbid, "offset": offset})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException("No similarity metrics are computed for the given (MBID, offset) combination.")
        return result.fetchone()


def get_similarity_row_id(id):
    # Get a single row of the similarity table by lowlevel.id
    with db.engine.connect() as connection:
        query = text("""
            SELECT *
              FROM similarity.similarity
             WHERE id = :id
        """)
        result = connection.execute(query, {"id": id})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException("No similarity metrics are computed for the given (MBID, offset) combination.")
        return result.fetchone()


def add_evaluation(user_id, eval_id, result_id, rating, suggestion):
    # Adds a row to the evaluation table.
    user_id = user_id or None
    with db.engine.begin() as connection:
        query = text("""
            INSERT INTO similarity.eval_feedback (user_id, eval_id, result_id, rating, suggestion)
                 VALUES (:user_id, :eval_id, :result_id, :rating, :suggestion)
            ON CONFLICT (user_id, eval_id, result_id)
             DO NOTHING
        """)
        connection.execute(query, {'user_id': user_id, 
                                   'eval_id': eval_id, 
                                   'result_id': result_id, 
                                   'rating': rating, 
                                   'suggestion': suggestion})


def submit_eval_results(query_id, result_ids, distances, params):
    """Submit a recording with its similar recordings and
    the parameters used to the similarity.eval_results table.

    Args:
        query_ids: lowlevel.id which is the subject of a
                   query for similarity.
        result_ids: A list of lowlevel.ids), referencing the resultant
                   recordings.
        distances: A list of integers, the distance between each resultant
                   recording and the query recording.
        params: A list of form [<metric_name>, <n_trees>, <distance_type>]
    """
    with db.engine.connect() as connection:
        param_query = text("""
            SELECT id
              FROM similarity.eval_params
             WHERE metric = :metric
               AND n_trees = :n_trees
               AND distance_type = :distance_type
        """)
        result = connection.execute(param_query, {"metric": params[0],
                                                  "n_trees": params[1],
                                                  "distance_type": params[2]})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException('There are no existing eval params for the index specified.')
        params_id = result.fetchone()["id"]

        insert_query = text("""
            INSERT INTO similarity.eval_results (query_id, similar_ids, distances, params)
                 VALUES (:query_id, :similar_ids, :distances, :params)
            ON CONFLICT 
          ON CONSTRAINT unique_eval_query_constraint
          DO UPDATE SET query_id = similarity.eval_results.query_id
              RETURNING id
        """)
        result = connection.execute(insert_query, {"query_id": query_id,
                                          "similar_ids": result_ids,
                                          "distances": distances,
                                          "params": params_id})
        eval_result_id = result.fetchone()[0]
        return eval_result_id


def check_for_eval_submission(user_id, eval_id):
    """Checks similarity.eval_feedback for whether
    or not a submission already exists with the given
    user_id and eval_id.

    Args:
        user_id: user.id associated with user submitting
        the eval form.
        eval_id: similarity.eval_results.id, indicating the
        query and results associated with the eval form.

    Returns:
        If a submission exists, returns True. Otherwise,
        returns False.
    """
    with db.engine.connect() as connection:
        query = text("""
            SELECT *
              FROM similarity.eval_feedback
             WHERE user_id = :user_id AND eval_id = :eval_id
        """)
        result = connection.execute(query, {"user_id": user_id,
                                            "eval_id": eval_id})
        if not result.rowcount:
            return False
        return True
