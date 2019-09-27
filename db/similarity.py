from __future__ import absolute_import
from flask import current_app

import db
from db.data import count_all_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
import db.similarity_stats
import similarity.metrics
import similarity.utils

from sqlalchemy import text
from collections import defaultdict


def add_metrics(batch_size):
    """Computes each metric from the similarity_metrics table for
    each recording in the lowlevel table, in batches.

    Args:
        batch_size: the number of recordings to be inserted, per batch.
    """
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
            print("error with row {}".format(id))
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
