import db
# import numpy as np

from sqlalchemy import text
from sqlalchemy.sql.expression import literal

HIGHLEVEL_MODELS_GENRE = ['genre_dortmund', 'genre_electronic']
PROCESS_LIMIT = 100
METRICS = ['mfcc']

def _get_highlevel_without_similarity(connection, limit=PROCESS_LIMIT):
    query = text("""
        SELECT src.id, src.model, src.data FROM highlevel_model AS src
        LEFT JOIN similarity_highlevel AS dst ON src.id = dst.id
        WHERE dst.vector IS NULL 
        LIMIT :limit
    """)
    return connection.execute(query, {'limit': limit})


def _transform(vector):
    """Transform as in Pearson distance calculation: subtract mean and normalize"""
    # vector = np.array(vector)
    # vector -= np.mean(vector)
    # vector /= np.linalg.norm(vector)
    return list(vector)


def populate_similarity_highlevel():
    with db.engine.begin() as connection:
        rows = _get_highlevel_without_similarity(connection)
        for row in rows:
            vector = row['data']['all'].values()
            query = text("""
                INSERT INTO similarity (id, mfcc) 
                VALUES (:id, cube(ARRAY[:vector]))
            """)
            connection.execute(query, {'id': row['id'], 'vector': tuple(vector)})


def get_similar_recordings(mbid, metric=None, limit=10):
    if metric is None:
        return {metric: get_similar_recordings(mbid, metric) for metric in METRICS}

    with db.engine.begin() as connection:
        query = text("""
            SELECT 
              gid
            FROM lowlevel
            JOIN similarity ON lowlevel.id = similarity.id
            ORDER BY cube(%(metric)s) <-> cube((
                SELECT %(metric)s 
                FROM similarity
                JOIN lowlevel on similarity.id = lowlevel.id
                WHERE lowlevel.gid=:gid
                LIMIT 1
              ))
            LIMIT :max
        """ % {'metric': metric})
        result = connection.execute(query, {'gid': mbid, 'max': limit})
        return result.fetchall()
