import numpy as np

import db.data
import db.stats
from operations import BaseMetric

NORMALIZATION_SAMPLE_SIZE = 10000


class LowLevelMetric(BaseMetric):
    path = ''
    indices = None

    def get_data(self, id):
        data = db.data.get_lowlevel_metric_feature(id, self.path)
        return data

    def length(self):
        return len(self.indices) if self.indices else 1


class NormalizedLowLevelMetric(LowLevelMetric):
    means = None
    stddevs = None

    def calculate_stats(self):
        # TODO: use same stats for weighted and normal metrics (e.g. mfccs and mfccsw)
        stats = db.stats.check_global_stats(self.name)
        if stats:
            # print('Global stats already calculated')
            self.means, self.stddevs = stats
            return

        # print('Calculating global stats for {}'.format(self.name))
        self.means = []
        self.stddevs = []

        if self.indices is None:
            mean, stddev = db.stats.calculate_stats_for_feature(self.path)
            self.means.append(mean)
            self.stddevs.append(stddev)
        else:
            for i in self.indices:
                # print('Index {} (out of {})'.format(i, len(self.indices)))
                mean, stddev = db.stats.calculate_stats_for_feature('{}->>{}'.format(self.path, i))
                self.means.append(mean)
                self.stddevs.append(stddev)

        db.stats.insert_similarity_stats(self.name, self.means, self.stddevs)

    def delete_stats(self):
        print('Deleting global stats')
        db.stats.delete_similarity_stats(self.name)

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))
        # normalize
        data = np.array(data)[self.indices]
        if np.count_nonzero(np.array(self.stddevs)):
            return (data - np.array(self.means)) / np.array(self.stddevs)
        else:
            return data


class WeightedNormalizedLowLevelMetric(NormalizedLowLevelMetric):
    weight = 0.95

    def __init__(self, connection):
        super(WeightedNormalizedLowLevelMetric, self).__init__(connection)
        indices = np.array(self.indices)
        indices -= np.min(indices)
        self.weight_vector = np.array([self.weight ** i for i in indices])

    def transform(self, data):  # add weights
        data = super(WeightedNormalizedLowLevelMetric, self).transform(data)
        return data * self.weight_vector


class MfccsMetric(NormalizedLowLevelMetric):
    name = 'mfccs'
    description = 'MFCCs'
    category = 'timbre'
    path = "data->'lowlevel'->'mfcc'->'mean'"
    indices = range(1, 13)


class WeightedMfccsMetric(WeightedNormalizedLowLevelMetric, MfccsMetric):
    name = 'mfccsw'
    description = 'MFCCs (weighted)'


class GfccsMetric(NormalizedLowLevelMetric):
    name = 'gfccs'
    description = 'GFCCs'
    category = 'timbre'
    path = "data->'lowlevel'->'gfcc'->'mean'"
    indices = range(1, 13)


class WeightedGfccsMetric(WeightedNormalizedLowLevelMetric, GfccsMetric):
    name = 'gfccsw'
    description = 'GFCCs (weighted)'


class CircularMetric(LowLevelMetric):
    def length(self):
        return 2

    def transform(self, data):
        """Wrap the value that around circle with overlaps on integers"""
        value = data * 2 * np.pi
        return np.array([np.cos(value), np.sin(value)])


KEYS_CIRCLE = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
KEYS_MAP = {KEYS_CIRCLE[i]: float(i) / 12 for i in range(12)}
SCALES_MAP = {'major': 0.0, 'minor': -3.0 / 12}


class KeyMetric(CircularMetric):
    name = 'key'
    path = "data->'tonal'"
    category = 'rhythm'
    description = 'Key/Scale'

    def transform(self, data):
        try:
            key_value = KEYS_MAP[data['key_key']]
            key_value += SCALES_MAP[data['key_scale']]
            return super(KeyMetric, self).transform(key_value)
        except KeyError:
            raise ValueError('Invalid key/scale values: {}, {}'.format(data['key_key'], data['key_scale']))


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


class OnsetRateMetric(LogCircularMetric):
    name = 'onsetrate'
    description = 'OnsetRate'
    category = 'rhythm'
    path = "data->'rhythm'->'onset_rate'"


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
            for model_id in self.models:
                if str(model_id) in data.keys():
                    model_data = data[str(model_id)]['all']
                    assert len(model_data) == 2
                    for key, value in model_data.items():
                        if not key.startswith('not'):
                            vector.append(value)
                            break
                else:
                    vector.append(None)
            return vector
        except KeyError:
            raise ValueError('Invalid data value: {}'.format(data))

    def length(self):
        return len(self.models)


class MoodsMetric(BinaryCollectiveMetric):
    name = 'moods'
    description = 'Moods'
    models = [
        11,  # mood_happy
        14,  # mood_sad
        9,   # mood_aggressive
        13,  # mood_relaxed
        12   # mood_party
    ]


class InstrumentsMetric(BinaryCollectiveMetric):
    name = 'instruments'
    description = 'Instruments'
    models = [
        8,   # mood_acoustic
        10,  # mood_electronic
        18   # voice_instrumental
    ]


class SingleClassifierMetric(HighLevelMetric):
    model = None
    size = None

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))

        if str(self.model) in data.keys():
            return data[str(self.model)]['all'].values()
        else:
            return [None]

    def length(self):
        return self.size


class DortmundGenreMetric(SingleClassifierMetric):
    name = 'dortmund'
    description = 'Genre (dortmund model)'
    model = 3
    size = 9


class RosamericaGenreMetric(SingleClassifierMetric):
    name = 'rosamerica'
    description = 'Genre (rosamerica model)'
    model = 5
    size = 8


class TzanetakisGenreMetric(SingleClassifierMetric):
    name = 'tzanetakis'
    description = 'Genre (tzanetakis model)'
    model = 6
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
