import db
import numpy as np

from sqlalchemy import text

PROCESS_LIMIT = 10
METRICS = {
    'tempo': 'bpm',
    'key': 'key',
    'tempo and key': 'array_cat(bpm, key)'
}

KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
KEYS_MAP = {KEYS[i]: float(i) / 12 for i in range(12)}
SCALES_MAP = {'major': 0, 'minor': -3.0 / 12}

MOOD_MODELS = [11, 14, 9, 13, 12]
INSTRUMENT_MODELS = [8, 10, 18]
GENRE_MODELS = [3, 5, 6]


# Common transformations

def _transform_circular(value):
    """Wrap the value that around circle with overlaps on integers"""
    value = value * 2*np.pi
    return [np.cos(value), np.sin(value)]


def _transform_pearson(vector):
    """Transform as in Pearson distance calculation: subtract mean and normalize"""
    vector = np.array(vector)
    vector -= np.mean(vector)
    vector /= np.linalg.norm(vector)
    return list(vector)


# Transformations of specific metrics

def _transform_bpm(data):
    bpm = data['rhythm']['bpm']
    return _transform_circular(np.log2(bpm))


def _transform_key(data):
    data = data['tonal']
    key_value = KEYS_MAP.get(data['key_key'], None)
    key_value += SCALES_MAP.get(data['key_scale'], None)
    return _transform_circular(key_value)


def _transform_mfccs(data):
    # TODO compute statistics
    return data['lowlevel']['mfcc']['mean']


def _transform_unary_classifiers(data, model_ids):
    vector = []
    for model_id in model_ids:
        vector.append(data[model_id - 1][0][0])
    return _transform_pearson(vector)


def _transform_moods(data):
    return _transform_unary_classifiers(data, MOOD_MODELS)


def _transform_instruments(data):
    return _transform_unary_classifiers(data, INSTRUMENT_MODELS)

# SQL wrappers

def _create_column(connection, name):


def _get_recordings_without_similarity(connection, name, limit=PROCESS_LIMIT):
    result = connection.execute("""
        SELECT ll.id FROM lowlevel AS ll
        LEFT JOIN similarity AS s ON ll.id = s.id
        WHERE s.%(metric)s IS NULL 
        LIMIT %(limit)s
    """ % {'metric': name, 'limit': limit})
    return result.fetchall()


def _get_data(connection, lowlevel_id):
    lowlevel_query = text("SELECT data FROM lowlevel_json WHERE id=:id")
    result = connection.execute(lowlevel_query, {'id': lowlevel_id})
    lowlevel_data = result.fetchone()

    highlevel_query = text("SELECT data, model FROM highlevel_model WHERE id=:id ORDER BY model ASC")
    result = connection.execute(lowlevel_query, {'id': lowlevel_id})
    highlevel_data = result.fetchall()

    return lowlevel_data, highlevel_data


def _render_sql_array(value):
    return 'ARRAY' + str(value)


def _get_highlevel_models(connection):
    query = text("SELECT id, model FROM model")
    result = connection.execute(query)
    return result.fetchall()


LL_METRICS = {
    'mfccs': _transform_mfccs,
    'bpm': _transform_bpm,
    'key': _transform_key
}

HL_METRICS = {

}


def populate_similarity(name, force):
    transform_func = LL_METRICS.get(name)
    is_highlevel = transform_func is None

    if is_highlevel:
        transform_func = HL_METRICS.get(name)

    if transform_func is None:
        raise ValueError('Invalid metric name: {}'.format(name))

    total = 0
    with db.engine.begin() as connection:
        if is_highlevel:
            highlevel_models = _get_highlevel_models(connection)

        rows = _get_recordings_without_similarity(connection)

        while len(rows) > 0:
            for row in rows:
                lowlevel_id = row[0]
                lowlevel_data, highlevel_data = _get_data(connection, lowlevel_id)

                bpm = _transform_bpm(lowlevel_data[0])
                key = _transform_key(lowlevel_data[0])
                mfccs, mfccs_w = _transform_mfccs(lowlevel_data[0])

                mood = _transform_mood(models, )

                query = text("""
                    INSERT INTO similarity (id, mfccs, mfccs_w, bpm, key) 
                    VALUES (%(id)s, %(mfccs)s, %(mfccs_w)s, %(bpm)s, %(key)s)
                """ % {
                    'id': lowlevel_id,
                    'mfccs': _render_sql_array(mfccs),
                    'mfccs_w': _render_sql_array(mfccs_w),
                    'bpm': _render_sql_array(bpm),
                    'key': _render_sql_array(key)
                })
                connection.execute(query)
                total += 1

            rows = _get_recordings_without_similarity(connection)
    return total


def get_similar_recordings(mbid, metric=None, limit=10):
    if metric is None:
        return {metric: get_similar_recordings(mbid, db_metric) for metric, db_metric in METRICS.items()}

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
