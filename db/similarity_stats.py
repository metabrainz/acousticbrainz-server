import db
from sqlalchemy import text

NORMALIZATION_SAMPLE_SIZE = 10000


def calculate_stats_for_feature(path):
    with db.engine.connect() as connection:
        query = text("""
            SELECT avg(x), stddev_pop(x)
              FROM (
            SELECT (%(path)s)::double precision AS x
              FROM lowlevel_json
             LIMIT :limit)
                AS res
        """ % {"path": path})
        result = connection.execute(query, {'limit': NORMALIZATION_SAMPLE_SIZE})
        return result.fetchone()


def check_global_stats(metric_name):
    with db.engine.connect() as connection:
        query = text("""
            SELECT means, stddevs
              FROM similarity_stats
             WHERE metric = :metric
        """)
        result = connection.execute(query, {"metric": metric_name})
        return result.fetchone()


def insert_similarity_stats(metric_name, means, stddevs):
    with db.engine.connect() as connection:
        query = text("""
            INSERT INTO similarity_stats (metric, means, stddevs)
                 VALUES (:metric, :means, :stddevs)
        """)
        connection.execute(query, {"metric": str(metric_name),
                                   "means": means,
                                   "stddevs": stddevs})


def delete_similarity_stats(metric):
    with db.engine.connect() as connection:
        query = text("""
            DELETE FROM similarity_stats
                  WHERE metric = :metric
        """)
        connection.execute(query, {"metric": metric})
