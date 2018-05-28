import db
import numpy as np

from sqlalchemy import text

HIGHLEVEL_MODELS_GENRE = ['genre_dortmund', 'genre_electronic']
PROCESS_LIMIT = 10
METRICS = ['key', 'bpm', 'array_cat(bpm, key)']

KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
KEYS_MAP = {KEYS[i]: float(i) / 12 for i in range(12)}
SCALES_MAP = {'major': 0, 'minor': -3.0 / 12}


def _transform_circular(value):
    """Wrap the value that around circle with overlaps on integers"""
    value = value * 2*np.pi
    return [np.cos(value), np.sin(value)]


def _transform_bpm(bpm):
    return _transform_circular(np.log2(bpm))


def _transform_key(key, scale):
    print(key, scale)
    key_value = KEYS_MAP.get(key, None)
    key_value += SCALES_MAP.get(scale, None)
    return _transform_circular(key_value)


def _transform_pearson(vector):
    """Transform as in Pearson distance calculation: subtract mean and normalize"""
    vector = np.array(vector)
    vector -= np.mean(vector)
    vector /= np.linalg.norm(vector)
    return list(vector)


def _transform_mfccs(mfccs):
    pass


def _get_recordings_without_similarity(connection, limit=PROCESS_LIMIT):
    query = text("""
        SELECT ll.id FROM lowlevel AS ll
        LEFT JOIN similarity AS s ON ll.id = s.id
        WHERE s.key IS NULL 
        LIMIT :limit
    """)
    result = connection.execute(query, {'limit': limit})
    return result.fetchall()


def _get_data(connection, lowlevel_id):
    lowlevel_query = text("""
        SELECT data FROM lowlevel_json WHERE id=:id;
    """)
    result = connection.execute(lowlevel_query, {'id': lowlevel_id})
    lowlevel_data = result.fetchone()

    highlevel_query = text("""
        SELECT data, model FROM highlevel_model WHERE id=:id
    """)
    result = connection.execute(lowlevel_query, {'id': lowlevel_id})
    highlevel_data = result.fetchall()
    return lowlevel_data, highlevel_data


def _render_sql_array(value):
    return 'ARRAY' + str(value)


def populate_similarity():
    total = 0
    with db.engine.begin() as connection:
        rows = _get_recordings_without_similarity(connection)
        while len(rows) > 0:
            for row in rows:
                lowlevel_id = row[0]
                lowlevel_data, highlevel_data = _get_data(connection, lowlevel_id)

                metric_bpm = _transform_bpm(lowlevel_data[0]['rhythm']['bpm'])
                tonal_data = lowlevel_data[0]['tonal']
                metric_key = _transform_key(tonal_data['key_key'], tonal_data['key_scale'])

                query = text("""
                    INSERT INTO similarity (id, bpm, key) 
                    VALUES (%(id)s, %(bpm)s, %(key)s)
                """ % {
                    'id': lowlevel_id,
                    'bpm': _render_sql_array(metric_bpm),
                    'key': _render_sql_array(metric_key)})
                connection.execute(query)
                total += 1

            rows = _get_recordings_without_similarity(connection)
    return total


def get_similar_recordings(mbid, metric=None, limit=10):
    if metric is None:
        return {metric: get_similar_recordings(mbid, metric) for metric in METRICS}

    with db.engine.begin() as connection:
        query = text("""
            SELECT 
              gid
            FROM lowlevel
            JOIN similarity ON lowlevel.id = similarity.id
            WHERE gid != :gid
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
