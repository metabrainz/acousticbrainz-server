from __future__ import absolute_import
from flask import current_app

import db
from db.data import count_all_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
import similarity.metrics
import similarity.utils

from sqlalchemy import text
from collections import defaultdict


def add_index(metric, batch_size=None, n_trees=10, distance_type='angular'):
    """Creates an annoy index for the specified metric, adds all items to the index."""
    print("Initializing index...")
    index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type)

    batch_size = batch_size or PROCESS_BATCH_SIZE
    offset = 0
    count = 0

    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT MAX(id)
              FROM similarity
        """)
        total = result.fetchone()[0]

        batch_query = text("""
            SELECT *
              FROM similarity
             ORDER BY id
             LIMIT :batch_size
            OFFSET :offset
        """)

        print("Inserting items...")
        while True:
            # Get ids and vectors for specific metric in batches
            batch_result = connection.execute(batch_query, { "batch_size": batch_size, "offset": offset })
            if not batch_result.rowcount:
                print("Finished adding items. Building index...")
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
            print("Items added: {}/{} ({:.3f}%)".format(offset, total, float(offset) / total * 100))

        index.build()
        print("Saving index...")
        index.save()


def get_all_metrics():
    with db.engine.begin() as connection:
        result = connection.execute("""
            SELECT category, metric, description
            FROM similarity_metrics
            WHERE visible = TRUE
        """)

        metrics = {}
        for category, metric, description in result.fetchall():
            if category not in metrics:
                metrics[category] = []
            metrics[category].append([metric, description])

        return metrics


def add_index(index, batch_size=None):
    """Adds all items to the initialized Annoy index."""
    batch_size = batch_size or PROCESS_BATCH_SIZE
    offset = 0
    count = 0

    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT MAX(id)
              FROM similarity
        """)
        total = result.fetchone()[0]

        batch_query = text("""
            SELECT *
              FROM similarity
             ORDER BY id
             LIMIT :batch_size
            OFFSET :offset
        """)

        print("Inserting items...")
        while True:
            # Get ids and vectors for specific metric in batches
            batch_result = connection.execute(batch_query, { "batch_size": batch_size, "offset": offset })
            if not batch_result.rowcount:
                print("Finished adding items. Building index...")
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
            print("Items added: {}/{} ({:.3f}%)".format(offset, total, float(offset) / total * 100))

        index.build()
        print("Saving index...")
        index.save()


def get_all_metrics():
    with db.engine.begin() as connection:
        result = connection.execute("""
            SELECT category, metric, description
            FROM similarity_metrics
            WHERE visible = TRUE
        """)

        metrics = {}
        for category, metric, description in result.fetchall():
            if category not in metrics:
                metrics[category] = []
            metrics[category].append([metric, description])

        return metrics


def add_metrics(force=False, batch_size=None):
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
              FROM similarity
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
              FROM similarity
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
              FROM similarity
             WHERE id = :id
        """)
        result = connection.execute(query, {"id": id})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException("No similarity metrics are computed for the given (MBID, offset) combination.")
        return result.fetchone()
