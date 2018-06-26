import db
import numpy as np

PROCESS_LIMIT = 100
STATS_SAMPLE = 10000

KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
KEYS_MAP = {KEYS[i]: float(i) / 12 for i in range(12)}
SCALES_MAP = {'major': 0, 'minor': -3.0 / 12}

MOOD_MODELS = [11, 14, 9, 13, 12]
INSTRUMENT_MODELS = [8, 10, 18]
GENRE_MODELS = [3, 5, 6]

DUPLICATE_SAFEGUARD = 3

# SQL wrappers


def _create_column(connection, metric):
    connection.execute("ALTER TABLE similarity ADD COLUMN IF NOT EXISTS %s DOUBLE PRECISION[]" % metric)
    connection.execute("CREATE INDEX IF NOT EXISTS %(metric)s_ndx_similarity ON similarity USING gist(cube(%(metric)s))"
                       % {'metric': metric})


def _delete_column(connection, metric):
    connection.execute("DROP INDEX IF EXISTS %s_ndx_similarity" % metric)
    connection.execute("ALTER TABLE similarity DROP COLUMN IF EXISTS %s " % metric)


def _clear_column(connection, metric):
    connection.execute("UPDATE similarity SET %(metric)s = NULL" % {'metric': metric})


def _get_recordings_without_similarity(connection, metric, limit=PROCESS_LIMIT):
    result = connection.execute("""
        SELECT id FROM similarity 
        WHERE %(metric)s IS NULL 
        LIMIT %(limit)s
    """ % {'metric': metric, 'limit': limit})
    rows = result.fetchall()
    if not rows:
        return []
    ids = zip(*rows)[0]
    return ids


def _update_similarity(connection, metric, row_id, vector):
    connection.execute("UPDATE similarity SET %(metric)s = %(value)s WHERE id = %(id)s" %
                       {'metric': metric, 'value': 'ARRAY' + str(vector), 'id': row_id})


def _get_lowlevel_data(connection, ids):
    result = connection.execute("SELECT id, data FROM lowlevel_json WHERE id IN %s" % str(ids))
    return result.fetchall()


def _get_highlevel_data(connection, ids):
    result = connection.execute("SELECT highlevel, jsonb_object_agg(model, data) "
                                "FROM highlevel_model WHERE highlevel IN %s "
                                "GROUP BY highlevel" % str(ids))
    return result.fetchall()


def _get_highlevel_models(connection):
    result = connection.execute("SELECT id, model FROM model")
    return result.fetchall()


def _compute_global_stats(connection, metric, field, indices):
    result = connection.execute("SELECT means, stddevs FROM similarity_stats WHERE metric='%s'" % metric)
    row = result.fetchone()
    print(row)
    if row:
        print('Global stats already calculated')
        return row

    print('Calculating global stats for {}'.format(metric))
    means = []
    stddevs = []
    for i in indices:
        print('Index {} (out of {})'.format(i, len(indices)))
        result = connection.execute("SELECT avg(x), stddev_pop(x)"
                                    "FROM (SELECT (%(field)s->>%(i)s)::double precision as x "
                                    "FROM lowlevel_json "
                                    "LIMIT %(limit)s) as res" %
                                    {'field': field, 'i': i, 'limit': STATS_SAMPLE})
        mean, stddev = result.fetchone()
        means.append(mean)
        stddevs.append(stddev)

    connection.execute("INSERT INTO similarity_stats (metric, means, stddevs) "
                       "VALUES (%(metric)s, %(means)s, %(stddevs)s)"
                       % {'metric': "'{}'".format(metric), 'means': 'ARRAY' + str(means), 'stddevs': 'ARRAY' + str(stddevs)})
    return means, stddevs


def _delete_global_stats(connection, metric):
    print('Deleting global stats')
    connection.execute("DELETE FROM similarity_stats WHERE metric='%s'" % metric)


def _calculate_mfccs_stats(connection):
    return _compute_global_stats(connection, 'mfccs', "data->'lowlevel'->'mfcc'->'mean'", range(1, 13))


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
    if not bpm:
        return [0, 0]
    return _transform_circular(np.log2(bpm))


def _transform_key(data):
    data = data['tonal']
    key_value = KEYS_MAP.get(data['key_key'], None)
    key_value += SCALES_MAP.get(data['key_scale'], None)
    return _transform_circular(key_value)


def _transform_mfccs(data, stats):
    means, stddevs = stats
    values = np.array(data['lowlevel']['mfcc']['mean'])[1:13]
    norms = (values - np.array(means)) / np.array(stddevs)
    return list(norms)


def _transform_unary_classifiers(data, model_ids):
    vector = []
    for model_id in model_ids:
        model_data = data[str(model_id)]['all']
        assert len(model_data) == 2
        for key, value in model_data.items():
            if not key.startswith('not'):
                vector.append(value)
                break
    return vector


def _transform_moods(data):
    return _transform_unary_classifiers(data, MOOD_MODELS)


def _transform_instruments(data):
    return _transform_unary_classifiers(data, INSTRUMENT_MODELS)


METRIC_FUNCS = {
    'mfccs':       (_get_lowlevel_data, _transform_mfccs, _calculate_mfccs_stats),
    'bpm':         (_get_lowlevel_data, _transform_bpm, None),
    'key':         (_get_lowlevel_data, _transform_key, None),
    'moods':       (_get_highlevel_data, _transform_moods, None),
    'instruments': (_get_highlevel_data, _transform_instruments, None),
}


# Helpers

def _hybridize(metric):
    metrics = metric.split('_')
    if len(metrics) > 1:
        return 'array_cat({})'.format(', '.join(metrics))
    return metric


# Public methods

def add_similarity(metric, force, total_limit, proc_limit):
    get_data, transform, get_stats = METRIC_FUNCS.get(metric)

    connection = db.engine.connect()

    _create_column(connection, metric)

    if force:
        _clear_column(connection, metric)

    result = connection.execute("SELECT count(*), count(%s) FROM similarity" % metric)
    total, past = result.fetchone()
    current = past
    stats = get_stats(connection) if get_stats else None

    proc_limit = proc_limit or PROCESS_LIMIT

    print('Started processing, {} / {} ({:.3f}%) already processed'.format(
        current, total, float(current) / total * 100))
    ids = _get_recordings_without_similarity(connection, metric, proc_limit)

    while len(ids) > 0 and (total_limit is None or current - past < total_limit):
        with connection.begin():
            for row_id, data in get_data(connection, ids):
                try:
                    vector = transform(data, stats) if get_stats else transform(data)
                    _update_similarity(connection, metric, row_id, vector)
                except RuntimeWarning as e:
                    print('Encountered error in transformation: {} (id={})'.format(e, row_id))

        current += len(ids)

        print('Processing {0} / {1} ({2:.3f}%)'.format(current, total, float(current) / total * 100))
        ids = _get_recordings_without_similarity(connection, metric, proc_limit)

    connection.close()

    return current


def remove_similarity(metric, leave_stats):
    with db.engine.begin() as connection:
        _delete_column(connection, metric)
        if not leave_stats:
            _delete_global_stats(connection, metric)


def get_similar_recordings(mbid, metric, limit=10):
    metric = _hybridize(metric)

    with db.engine.begin() as connection:
        result = connection.execute("""
          SELECT DISTINCT gid, dist FROM (
            SELECT 
              gid,
              cube(%(metric)s) <-> cube((
                SELECT %(metric)s 
                FROM similarity
                JOIN lowlevel on similarity.id = lowlevel.id
                WHERE lowlevel.gid='%(gid)s'
                LIMIT 1
              )) as dist
            FROM lowlevel
            JOIN similarity ON lowlevel.id = similarity.id
            WHERE gid != '%(gid)s'
            ORDER BY dist
              LIMIT %(max_extra)s) AS res
          ORDER BY dist
          LIMIT %(max)s
        """ % {'metric': metric, 'gid': mbid, 'max': limit, 'max_extra': limit * DUPLICATE_SAFEGUARD})
        return result.fetchall()


def init_similarity():
    with db.engine.begin() as connection:
        connection.execute("INSERT INTO similarity(id) SELECT id FROM lowlevel")


def add_hybrid_similarity(metric):
    metric_str = _hybridize(metric)
    with db.engine.begin() as connection:
        connection.execute("CREATE INDEX IF NOT EXISTS %(name)s_ndx_similarity ON similarity "
                           "USING gist(cube(%(metric)s))" % {'name': metric, 'metric': metric_str})
