from __future__ import absolute_import

import db
from db.data import count_all_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from similarity.index_model import AnnoyModel
import similarity.metrics
import similarity.exceptions

from sqlalchemy import text

PROCESS_BATCH_SIZE = 10000


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


def insert_similarity_meta(metric, hybrid, description, category):
    # Adds a new row to similarity_metrics, containing metadata about a metric.
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
    # Removes the metadata about a given metric.
    with db.engine.connect() as connection:
        query = text("""
            DELETE FROM similarity_metrics
                  WHERE metric = :metric
        """)
        connection.execute(query, {"metric": metric})


def create_similarity_metric(metric, clear):
    # Adds metric column to similarity table, holding a vector for each recording.
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
    # Removes a metric column.
    with db.engine.connect() as connection:
        query = text("""
            ALTER TABLE similarity
            DROP COLUMN
              IF EXISTS :metric
        """)
        connection.execute(query, {"metric": metric})


def remove_visibility(metric):
    # Removes visibility of a metric in similarity_metrics table.
    with db.engine.connect() as connection:
        query = text("""
            UPDATE similarity_metrics
               SET visible = FALSE
             WHERE metric = :metric
        """)
        connection.execute(query, {"metric": metric})


def get_metric_dimension(metric_name):
    # Get dimension of vectors for a metric in similarity table
    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT *
              FROM similarity
             LIMIT 1
        """)
        try:
            dimension = len(result.fetchone()[metric_name])
            return dimension
        except (ValueError, TypeError):
            raise similarity.exceptions.IndexNotFoundException("No existing metric named \"{}\"".format(metric_name))


def get_similarity_metrics_row_mbid(mbid, offset):
    # Get a single row of the similarity_metrics table by (MBID, offset) combination
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
        result = connection.execute(query, { "mbid": mbid, "submission_offset": offset})
        return result.fetchone()


def get_similarity_metrics_row_id(id):
    # Get a single row of the similarity_metrics table by lowlevel.id
    with db.engine.connect() as connection:
        query = text("""
            SELECT *
              FROM similarity
             WHERE id = :id
        """)
        result = connection.execute(query, {"id": id})
        if not result.rowcount:
            raise similarity.exceptions.ItemNotFoundException
        return result.fetchone()
