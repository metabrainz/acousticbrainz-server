import db
import db.data

import numpy as np


class BaseMetric(object):
    name = ''
    description = ''
    category = ''


class LowLevelMetric(BaseMetric):
    path = ''
    indices = None

    def get_data(self, id):
        data = db.data.get_lowlevel_metric_feature(id, self.path)
        return data

    def get_feature_data(self, data):
        # Get lowlevel from data, extract path
        if data:
            for key in self.keys:
                data = data[key]
            return data
        return None

    def length(self):
        return len(self.indices) if self.indices else 1


class NormalizedLowLevelMetric(LowLevelMetric):
    means = None
    stddevs = None

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))
        # Normalize
        data = np.array(data)[self.indices]
        if np.count_nonzero(np.array(self.stddevs)):
            return list((data - np.array(self.means)) / np.array(self.stddevs))
        else:
            return list(data)


class WeightedNormalizedLowLevelMetric(NormalizedLowLevelMetric):
    weight = 0.95

    def __init__(self):
        indices = np.array(self.indices)
        indices -= np.min(indices)
        self.weight_vector = np.array([self.weight ** i for i in indices])

    def transform(self, data):  # add weights
        data = super(WeightedNormalizedLowLevelMetric, self).transform(data)
        return list(data * self.weight_vector)


class MfccsMetric(NormalizedLowLevelMetric):
    name = 'mfccs'
    description = 'MFCCs'
    category = 'timbre'
    path = "data->'lowlevel'->'mfcc'->'mean'"
    keys = ['mfcc']
    indices = range(0, 13)


class WeightedMfccsMetric(WeightedNormalizedLowLevelMetric, MfccsMetric):
    name = 'mfccsw'
    description = 'MFCCs (weighted)'


class GfccsMetric(NormalizedLowLevelMetric):
    name = 'gfccs'
    description = 'GFCCs'
    category = 'timbre'
    path = "data->'lowlevel'->'gfcc'->'mean'"
    keys = ['gfcc']
    indices = range(0, 13)


class WeightedGfccsMetric(WeightedNormalizedLowLevelMetric, GfccsMetric):
    name = 'gfccsw'
    description = 'GFCCs (weighted)'


class CircularMetric(LowLevelMetric):
    def length(self):
        return 2

    def transform(self, data):
        """Wrap the value that around circle with overlaps on integers"""
        value = data * 2 * np.pi
        return list(np.array([np.cos(value), np.sin(value)]))


KEYS_CIRCLE = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
KEYS_MAP = {KEYS_CIRCLE[i]: float(i) / 12 for i in range(12)}
SCALES_MAP = {'major': 0.0, 'minor': -3.0 / 12}


class KeyMetric(CircularMetric):
    name = 'key'
    path = "data->'tonal'"
    keys = ['key']
    category = 'rhythm'
    description = 'Key/Scale'

    def transform(self, data):
        try:
            key_value = KEYS_MAP[data['key_key']]
            key_value += SCALES_MAP[data['key_scale']]
            return super(KeyMetric, self).transform(key_value)
        except KeyError:
            raise ValueError('Invalid data value: {}'.format(data))


class LogCircularMetric(CircularMetric):
    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))
        return super(LogCircularMetric, self).transform(np.log2(data))


class BpmMetric(LogCircularMetric):
    name = 'bpm'
    description = 'BPM'
    category = 'rhythm'
    path = "data->'rhythm'->'bpm'"
    keys = ['bpm']


class OnsetRateMetric(LogCircularMetric):
    name = 'onsetrate'
    description = 'OnsetRate'
    category = 'rhythm'
    path = "data->'rhythm'->'onset_rate'"
    keys = ['onset_rate']


class HighLevelMetric(BaseMetric):
    category = 'high-level'

    def get_data(self, id):
        data = db.data.get_highlevel_models(id)
        return data


class BinaryCollectiveMetric(HighLevelMetric):
    models = None

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))

        vector = []
        try:
            for model in self.models:
                if model in data.keys():
                    model_data = data[model]['all']
                    assert len(model_data) == 2
                    for key, value in model_data.items():
                        if not key.startswith('not'):
                            vector.append(value)
                            break
                else:
                    vector.append(0)
            return vector
        except KeyError:
            raise ValueError('Invalid data value: {}'.format(data))

    def length(self):
        return len(self.models)


class MoodsMetric(BinaryCollectiveMetric):
    name = 'moods'
    description = 'Moods'
    models = [
        'mood_happy',
        'mood_sad',
        'mood_aggressive',
        'mood_relaxed',
        'mood_party'
    ]


class InstrumentsMetric(BinaryCollectiveMetric):
    name = 'instruments'
    description = 'Instruments'
    models = [
        'mood_acoustic',
        'mood_electronic',
        'voice_instrumental'
    ]


class SingleClassifierMetric(HighLevelMetric):
    model = None
    size = None

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))

        if self.model in data.keys():
            return data[self.model]['all'].values()
        else:
            return [0] * self.length()

    def length(self):
        return self.size


class DortmundGenreMetric(SingleClassifierMetric):
    name = 'dortmund'
    description = 'Genre (dortmund model)'
    model = 'genre_dortmund'
    size = 9


class RosamericaGenreMetric(SingleClassifierMetric):
    name = 'rosamerica'
    description = 'Genre (rosamerica model)'
    model = 'genre_rosamerica'
    size = 8


class TzanetakisGenreMetric(SingleClassifierMetric):
    name = 'tzanetakis'
    description = 'Genre (tzanetakis model)'
    model = 'genre_tzanetakis'
    size = 10


_BASE_METRICS_LIST = [
    # Low-level
    MfccsMetric,
    WeightedMfccsMetric,
    GfccsMetric,
    WeightedGfccsMetric,
    KeyMetric,
    BpmMetric,
    OnsetRateMetric,
    # High-level
    MoodsMetric,
    InstrumentsMetric,
    DortmundGenreMetric,
    RosamericaGenreMetric,
    TzanetakisGenreMetric
]

BASE_METRICS = {cls.name: cls for cls in _BASE_METRICS_LIST}


# Highlevel models required to compute all similarity metrics
BASE_MODELS = [("danceability", "v2.1_beta1", "show"),
               ("gender", "v2.1_beta1", "show"),
               ("genre_dortmund", "v2.1_beta1", "show"),
               ("genre_electronic", "v2.1_beta1", "show"),
               ("genre_rosamerica", "v2.1_beta1", "show"),
               ("genre_tzanetakis", "v2.1_beta1", "show"),
               ("ismir04_rhythm", "v2.1_beta1", "show"),
               ("mood_acoustic", "v2.1_beta1", "show"),
               ("mood_aggressive", "v2.1_beta1", "show"),
               ("mood_electronic", "v2.1_beta1", "show"),
               ("mood_happy", "v2.1_beta1", "show"),
               ("mood_party", "v2.1_beta1", "show"),
               ("mood_relaxed", "v2.1_beta1", "show"),
               ("mood_sad", "v2.1_beta1", "show"),
               ("moods_mirex", "v2.1_beta1", "show"),
               ("timbre", "v2.1_beta1", "show"),
               ("tonal_atonal", "v2.1_beta1", "show"),
               ("voice_instrumental", "v2.1_beta1", "show")]
