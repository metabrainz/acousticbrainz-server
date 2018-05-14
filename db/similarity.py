import db
import numpy as np

from sqlalchemy import text

HIGHLEVEL_MODELS_GENRE = ['genre_dortmund', 'genre_electronic']
PROCESS_LIMIT = 100


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
    vector = np.array(vector)
    vector -= np.mean(vector)
    vector /= np.linalg.norm(vector)
    return list(vector)


def populate_similarity_highlevel():
    with db.engine.begin() as connection:
        rows = _get_highlevel_without_similarity(connection)
        for row in rows:
            vector = row['data']['all'].values()
            query = text("""
                INSERT INTO similarity_highlevel (id, vector) 
                VALUES (:id, cube(ARRAY[:vector]))
            """)
            connection.execute(query, {'id': row['id'], 'vector': tuple(vector)})

