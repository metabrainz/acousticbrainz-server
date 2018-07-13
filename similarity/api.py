import db
from utils import to_db_column
import numpy as np

NORMALIZATION_SAMPLE_SIZE = 10000
PROCESS_BATCH_SIZE = 10000
QUERY_PADDING_FACTOR = 3
QUERY_RESULT_SIZE = 10


def get_similar_recordings(mbid, metric, limit=None):
    metric = to_db_column(metric)
    limit = limit or QUERY_RESULT_SIZE

    with db.engine.begin() as connection:
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
        return np.unique(rows)[:limit]
