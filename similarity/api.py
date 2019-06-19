import db
from operations import HybridMetric
import numpy as np

NORMALIZATION_SAMPLE_SIZE = 10000
PROCESS_BATCH_SIZE = 10000
QUERY_PADDING_FACTOR = 3
QUERY_RESULT_SIZE = 10


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


def get_similar_recordings(mbid, metric, limit=QUERY_RESULT_SIZE):
    with db.engine.begin() as connection:
        # check both existence and if it is hybrid
        # TODO (refactor): separate metric info from similarity
        result = connection.execute("SELECT is_hybrid, category, description FROM similarity_metrics WHERE metric='%s'" % metric)
        row = result.fetchone()
        if not row:
            return None

        # translate metric name to array_cat expression if hybrid
        is_hybrid, category, description = row
        metric = HybridMetric.get_pseudo_column(metric) if is_hybrid else metric

        # actual query
        result = connection.execute("""
            SELECT 
              gid
            FROM lowlevel
            JOIN similarity ON lowlevel.id = similarity.id
            WHERE gid != '%(gid)s'
            ORDER BY cube(%(metric)s) <-> cube((
                SELECT %(metric)s 
                FROM similarity
                JOIN lowlevel on similarity.id = lowlevel.id
                WHERE lowlevel.gid='%(gid)s'
                LIMIT 1
              )) 
            LIMIT %(max)s
        """ % {'metric': metric, 'gid': mbid, 'max': limit * QUERY_PADDING_FACTOR})
        rows = result.fetchall()
        rows = zip(*rows)
        return list(np.unique(rows)[:limit]), category, description


def add_evaluation(user_id, query_mbid, result_mbids, metric, rating, suggestion='NULL'):
    result_mbids_str = 'NULL' if result_mbids is None else 'ARRAY' + str(result_mbids)
    user_id = user_id or 'NULL'

    with db.engine.begin() as connection:
        connection.execute("""
            INSERT INTO similarity_eval (user_id, query_mbid, result_mbids, metric, rating, suggestion) 
            VALUES (%(user)s, '%(query_mbid)s', %(result_mbids)s, '%(metric)s', %(rating)s, %(suggestion)s)
        """ % {'user': user_id, 'query_mbid': query_mbid, 'result_mbids': result_mbids_str, 'metric': metric,
               'rating': rating, 'suggestion': suggestion})

