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


# SQL wrappers

def _create_column(connection, metric):
    connection.execute("ALTER TABLE similarity ADD COLUMN IF NOT EXISTS %s DOUBLE PRECISION[]" % metric)
    connection.execute("CREATE INDEX IF NOT EXISTS %(metric)s_ndx_similarity ON similarity USING gist(cube(%(metric)s))"
                       % {'metric': metric})


def _add_hybrid_index(connection, metrics):
    name = '_'.join(metrics)
    metric_str = 'array_cat({})'.format(', '.join(metrics))
    connection.execute("CREATE INDEX IF NOT EXISTS %(name)s_ndx_similarity ON similarity USING gist(cube(%(metric)s))"
                       % {'name': name, 'metric': metric_str})


def _clear_column(connection, metric):
    connection.execute("UPDATE similarity SET %(metric)s = NULL" % {'metric': metric})


def _get_recordings_without_similarity(connection, metric, limit=PROCESS_LIMIT):
    result = connection.execute("""
        SELECT ll.id FROM lowlevel AS ll
        LEFT JOIN similarity AS s ON ll.id = s.id
        WHERE s.%(metric)s IS NULL 
        LIMIT %(limit)s
    """ % {'metric': metric, 'limit': limit})
    return result.fetchall()


def _get_lowlevel_data(connection, lowlevel_id):
    result = connection.execute("SELECT data FROM lowlevel_json WHERE id=%s" % lowlevel_id)
    return result.fetchone()[0]


def _get_highlevel_data(connection, lowlevel_id):
    result = connection.execute("SELECT data, model FROM highlevel_model WHERE id=%s ORDER BY model ASC" % lowlevel_id)
    return result.fetchall()


def _get_highlevel_models(connection):
    query = text("SELECT id, model FROM model")
    result = connection.execute(query)
    return result.fetchall()


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


METRIC_FUNCS = {
    'mfccs':       (_get_lowlevel_data, _transform_mfccs),
    'bpm':         (_get_lowlevel_data, _transform_bpm),
    'key':         (_get_lowlevel_data, _transform_key),
    'moods':       (_get_highlevel_data, _transform_moods),
    'instruments': (_get_highlevel_data, _transform_instruments),
}


# Public methods

def add_similarity(metric, force):
    get_data, transform = METRIC_FUNCS.get(metric)

    total = 0
    with db.engine.begin() as connection:
        _create_column(connection, metric)

        if force:
            _clear_column(connection, metric)

        rows = _get_recordings_without_similarity(connection, metric)

        while len(rows) > 0:
            for row in rows:
                lowlevel_id = row[0]
                data = get_data(connection, lowlevel_id)
                vector = transform(data)
                connection.execute("UPDATE similarity SET %(metric)s = %(value)s WHERE id = %(id)s" %
                                   {'metric': metric, 'value': 'ARRAY' + str(vector), 'id': lowlevel_id})
                total += 1

            rows = _get_recordings_without_similarity(connection, metric)

    return total


def get_similar_recordings(mbid, metric=None, limit=10):
    if metric is None:
        return {metric: get_similar_recordings(mbid, db_metric) for metric, db_metric in METRICS.items()}

    with db.engine.begin() as connection:
        result = connection.execute("""
            SELECT 
              gid
            FROM lowlevel
            JOIN similarity ON lowlevel.id = similarity.id
            WHERE gid != :gid
            ORDER BY cube(%(metric)s) <-> cube((
                SELECT %(metric)s 
                FROM similarity
                JOIN lowlevel on similarity.id = lowlevel.id
                WHERE lowlevel.gid=%(gid)s
                LIMIT 1
              ))
            LIMIT %(max)s
        """ % {'metric': metric, 'gid': mbid, 'max': limit})
        return result.fetchall()


def init_similarity():
    with db.engine.begin() as connection:
        result = connection.execute("INSERT INTO similarity(id) SELECT id FROM lowlevel")
