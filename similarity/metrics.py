import numpy as np

NORMALIZATION_SAMPLE_SIZE = 10000


class Metric(object):
    name = ''
    description = ''

    def __init__(self, connection):
        self.connection = connection


class LowLevelMetric(Metric):
    path = ''
    indices = None

    def get_data_batch(self, ids):
        result = self.connection.execute("SELECT id, %(path)s FROM lowlevel_json WHERE id IN %(ids)s" %
                                         {'ids': str(ids), 'path': self.path})
        return result.fetchall()

    def length(self):
        return len(self.indices) if self.indices else 1


class NormalizedLowLevelMetric(LowLevelMetric):
    means = None
    stddevs = None

    def _calculate_stats_for(self, path):
        result = self.connection.execute("SELECT avg(x), stddev_pop(x) "
                                         "FROM (SELECT (%(path)s)::double precision as x "
                                         "FROM lowlevel_json "
                                         "LIMIT %(limit)s) as res" %
                                         {'path': path, 'limit': NORMALIZATION_SAMPLE_SIZE})
        return result.fetchone()

    def calculate_stats(self):
        # TODO: use same stats for weighted and normal metrics (e.g. mfccs and mfccsw)
        result = self.connection.execute("SELECT means, stddevs FROM similarity_stats WHERE metric='%s'" % self.name)
        row = result.fetchone()

        if row:
            print('Global stats already calculated')
            self.means, self.stddevs = row
            return

        print('Calculating global stats for {}'.format(self.name))
        self.means = []
        self.stddevs = []

        if self.indices is None:
            self.means[0], self.stddevs[0] = self._calculate_stats_for(self.path)
        else:
            for i in self.indices:
                print('Index {} (out of {})'.format(i, len(self.indices)))
                mean, stddev = self._calculate_stats_for('{}->>{}'.format(self.path, i))
                self.means.append(mean)
                self.stddevs.append(stddev)

        self.connection.execute("INSERT INTO similarity_stats (metric, means, stddevs) "
                                "VALUES (%(metric)s, %(means)s, %(stddevs)s)"
                                % {'metric': "'{}'".format(self.name),
                                   'means': 'ARRAY' + str(self.means),
                                   'stddevs': 'ARRAY' + str(self.stddevs)})

    def delete_stats(self):
        print('Deleting global stats')
        self.connection.execute("DELETE FROM similarity_stats WHERE metric='%s'" % self.name)

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))
        # normalize
        data = np.array(data)[self.indices]
        return (data - np.array(self.means)) / np.array(self.stddevs)


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
    path = "data->'lowlevel'->'mfcc'->'mean'"
    indices = range(1, 13)


class WeightedMfccsMetric(WeightedNormalizedLowLevelMetric, MfccsMetric):
    name = 'mfccsw'


class GfccsMetric(NormalizedLowLevelMetric):
    name = 'gfccs'
    description = 'GFCCs'
    path = "data->'lowlevel'->'gfcc'->'mean'"
    indices = range(1, 13)


class WeightedGfccsMetric(WeightedNormalizedLowLevelMetric, GfccsMetric):
    name = 'gfccsw'


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
    path = "data->'rhythm'->'bpm'"


class OnsetRateMetric(LogCircularMetric):
    name = 'onsetrate'
    description = 'Onset rate'
    path = "data->'rhythm'->'onset_rate'"


class HighLevelMetric(Metric):
    def get_data_batch(self, ids):
        result = self.connection.execute("SELECT highlevel, jsonb_object_agg(model, data) "
                                         "FROM highlevel_model WHERE highlevel IN %s "
                                         "GROUP BY highlevel" % str(ids))
        rows = result.fetchall()
        if len(rows) < len(ids):
            existing_ids = [row[0] for row in rows]
            for row_id in set(ids) - set(existing_ids):
                rows.append((row_id, None))
        return rows


class BinaryCollectiveMetric(HighLevelMetric):
    models = None

    def transform(self, data):
        if not data:
            raise ValueError('Invalid data value: {}'.format(data))

        vector = []
        try:
            for model_id in self.models:
                model_data = data[str(model_id)]['all']
                assert len(model_data) == 2
                for key, value in model_data.items():
                    if not key.startswith('not'):
                        vector.append(value)
                        break
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

        return data[str(self.model)]['all'].values()

    def length(self):
        return self.size


class DortmundGenreMetric(SingleClassifierMetric):
    name = 'dortmund'
    description = 'Genre (dortmund)'
    model = 3
    size = 9


class RosamericaGenreMetric(SingleClassifierMetric):
    name = 'rosamerica'
    description = 'Genre (rosamerica)'
    model = 5
    size = 8


class TzanetakisGenreMetric(SingleClassifierMetric):
    name = 'tzanetakis'
    description = 'Genre (tzanetakis)'
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
