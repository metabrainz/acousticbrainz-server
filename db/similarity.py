from __future__ import absolute_import

import db
from db.data import count_all_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
import similarity.metrics

from sqlalchemy import text

PROCESS_BATCH_SIZE = 10000


def add_metrics(force=False, batch_size=None):
    batch_size = batch_size or PROCESS_BATCH_SIZE
    lowlevel_count = count_all_lowlevel()

    with db.engine.connect() as connection:
        metrics = similarity.utils.init_metrics(force=force)
        offset = count_similarity()
        print("Processed {} / {} ({:.3f}%)".format(offset,
                                                   lowlevel_count,
                                                   float(offset) / lowlevel_count * 100))

        while count_similarity() < lowlevel_count:
            batch_query = text("""
                SELECT id
                  FROM lowlevel
              ORDER BY id
                 LIMIT :batch_size
                OFFSET :offset
            """)
            result = connection.execute(batch_query, {"batch_size": batch_size, "offset": offset})
            if not result.rowcount:
                print("Metric {} added for all recordings".format(metric.name))
                break

            for row in result.fetchall():
                submit_similarity_by_id(row["id"], metrics=metrics)

            offset = count_similarity()
            print("Processed {} / {} ({:.3f}%)".format(offset,
                                                       lowlevel_count,
                                                       float(offset) / lowlevel_count * 100))


def insert_similarity(id, vectors_info):
    """Inserts a row of similarity vectors for a given lowlevel.id into
    the similarity table.

        Args: lowlevel.id to be submitted
              vectors_info, list of tuples of the form:
              (metric_name, vector, isnan)
    """
    with db.engine.connect() as connection:
        values = []
        for metric, vector, isnan in vectors_info:
            value = ('ARRAY' + ('[' + ', '.join(["'NaN'::double precision"] *
                     len(vector)) + ']' if isnan else str(list(vector))))
            values.append(value)

        values_string = ', '.join(values)
        query = text("""
            INSERT INTO similarity (
                        id,
                        mfccs,
                        mfccsw,
                        gfccs,
                        gfccsw,
                        key,
                        bpm,
                        onsetrate,
                        moods,
                        instruments,
                        dortmund,
                        rosamerica,
                        tzanetakis)
                 VALUES (
                        :id,
                        %(values)s)
            ON CONFLICT (id)
             DO NOTHING
        """ % {"values": values_string})
        connection.execute(query, {'id': id})


def count_similarity():
    # Get total number of submissions in similarity table
    with db.engine.connect() as connection:
        query = text("""
            SELECT COUNT(*)
              FROM similarity
        """)
        result = connection.execute(query)
        return result.fetchone()[0]


def submit_similarity_by_id(id, metrics=None):
    """Computes similarity metrics for a single recording specified
    by lowlevel.id, then inserts the metrics as a new row in the
    similarity table."""
    try:
        id = int(id)
    except ValueError:
        raise BadDataException('Parameter `id` must be an integer.')

    # Check that lowlevel submission exists for given id
    if not db.data.check_for_submission(id):
        raise NoDataFoundException('No submission for parameter `id`.')

    if not metrics:
        metrics = similarity.utils.init_metrics()

    vectors_info = []
    for metric in metrics:
        data = metric.get_data(id)
        try:
            vector = metric.transform(data)
            isnan = False
        except ValueError:
            vector = [None] * metric.length()
            isnan = True
        vectors_info.append((metric.name, vector, isnan))

    insert_similarity(id, vectors_info)


def submit_similarity_by_mbid(mbid, offset):
    """Computes similarity metrics for a single recording specified
    by (mbid, offset) combination, then inserts the metrics as a new
    row in the similarity table."""
    id = db.data.get_lowlevel_id(mbid, offset)
    submit_similarity_by_id(id)


# TODO: Write tests for these and for stats, also add docstrings.
def insert_similarity_meta(metric, hybrid, description, category):
    with db.engine.connect() as connection:
        metrics_query = text("""
            INSERT INTO similarity_metrics (metric, is_hybrid, description, category, visible)
                 VALUES (:metric, :hybrid, :description, :category, TRUE)
            ON CONFLICT (metric)
          DO UPDATE SET visible=TRUE
        """)
        connection.execute(metrics_query, {'metric': metric,
                                           'hybrid': hybrid,
                                           'description': description,
                                           'category': category})


def delete_similarity_meta(metric):
    with db.engine.connect() as connection:
        query = text("""
            DELETE FROM similarity_metrics
                  WHERE metric = :metric
        """)
        connection.execute(query, {"metric": metric})


def create_similarity_metric(metric, clear):
    with db.engine.connect() as connection:
        query = text("""
            ALTER TABLE similarity
             ADD COLUMN
          IF NOT EXISTS %s DOUBLE PRECISION[]
        """ % metric)
        connection.execute(query)

        if clear:
            # Delete all existing rows.
            query = text("""
                DELETE FROM ONLY similarity
            """)
        connection.execute(query)


def delete_similarity_metric(metric):
    with db.engine.connect() as connection:
        query = text("""
            ALTER TABLE similarity
            DROP COLUMN
              IF EXISTS %s
        """ % metric)
        connection.execute(query)


def remove_visibility(metric):
    with db.engine.connect() as connection:
        query = text("""
            UPDATE similarity_metrics
               SET visible = FALSE
             WHERE metric = :metric
        """)
        connection.execute(query, {"metric": metric})
