import db
import numpy as np


KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
KEYS_MAP = {KEYS[i]: float(i) / 12 for i in range(12)}
SCALES_MAP = {'major': 0, 'minor': -3.0 / 12}


MOOD_MODELS = [11, 14, 9, 13, 12]
INSTRUMENT_MODELS = [8, 10, 18]
GENRE_MODELS = [3, 5, 6]
DORTMUND_MODEL = 3
ROSAMERICA_MODEL = 5
TZANETAKIS_MODEL = 6

DUPLICATE_SAFEGUARD = 3

# SQL wrappers


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


def _transform_classifier(data, model_id):
    return data[str(model_id)]['all'].values()


METRIC_FUNCS = {
    'bpm':          (_get_lowlevel_data, _transform_bpm, None),
    'onsetrate':    (_get_lowlevel_data, _transform_onset_rate, None),
    'key':          (_get_lowlevel_data, _transform_key, None),

    'mfccs':        (_get_lowlevel_data, _transform_mfccs, _calculate_mfccs_stats),
    'mfccsw':       (_get_lowlevel_data, _transform_mfccs_w, _calculate_mfccs_stats),
    'gfccs':        (_get_lowlevel_data, _transform_gfccs, _calculate_gfccs_stats),
    'gfccsw':       (_get_lowlevel_data, _transform_gfccs_w, _calculate_gfccs_stats),

    'dortmund':     (_get_highlevel_data, lambda(data): _transform_classifier(data, DORTMUND_MODEL), None),
    'tzanetakis':   (_get_highlevel_data, lambda(data): _transform_classifier(data, TZANETAKIS_MODEL), None),
    'rosamerica':   (_get_highlevel_data, lambda(data): _transform_classifier(data, ROSAMERICA_MODEL), None),

    'moods':        (_get_highlevel_data, lambda(data): _transform_unary_classifiers(data, MOOD_MODELS), None),
    'instruments':  (_get_highlevel_data, lambda(data): _transform_unary_classifiers(data, INSTRUMENT_MODELS), None),
}


# Helpers



# Public methods


def get_similar_recordings(mbid, metric, limit=10):
    metric = _hybridize(metric)

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
        """ % {'metric': metric, 'gid': mbid, 'max': limit * DUPLICATE_SAFEGUARD})
        rows = result.fetchall()
        rows = zip(*rows)
        return np.unique(rows)[:limit]


