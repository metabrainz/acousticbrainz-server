from flask import current_app

import numpy as np


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

    def get_nan(self):
        size = len(self.indices) if self.indices else 1
        return ['NaN'] * size


class NormalizedLowLevelMetric(LowLevelMetric):
    means = None
    stddevs = None
    sample_size = current_app.config["NORMALIZATION_SAMPLE_SIZE"]

    def _calculate_stats_for(self, path):
        result = self.connection.execute("SELECT avg(x), stddev_pop(x) "
                                         "FROM (SELECT (%(path)s)::double precision as x "
                                         "FROM lowlevel_json "
                                         "LIMIT %(limit)s) as res" %
                                         {'path': path, 'limit': self.sample_size})
        return result.fetchone()

    def calculate_stats(self):
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
    def get_nan(self):
        return ['NaN'] * 2

    def transform(self, data):
        """Wrap the value that around circle with overlaps on integers"""
        value = data * 2 * np.pi
        return np.array([np.cos(value), np.sin(value)])


class KeyMetric(CircularMetric):
    keys = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'F']
    keys_map = {keys[i]: float(i) / 12 for i in range(12)}
    scales_map = {'major': 0, 'minor': -3.0 / 12}

    path = 'data->tonal'

    def transform(self, data):
        try:
            key_value = self.keys[data['key_key']]
            key_value += self.scales_map[data['key_scale']]
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
    path = "data->rhythm->>bpm"


class OnsetRateMetric(LogCircularMetric):
    name = 'onsetrate'
    description = 'Onset rate'
    path = "data->rhythm->>onset_rate"


class HighLevelMetric(Metric):
    def get_data_batch(cls, connection, ids):
        result = connection.execute("SELECT highlevel, jsonb_object_agg(model, data) "
                                    "FROM highlevel_model WHERE highlevel IN %s "
                                    "GROUP BY highlevel" % str(ids))
        return result.fetchall()


_BASE_METRICS_LIST = [
    MfccsMetric,
    WeightedMfccsMetric,
    GfccsMetric,
    WeightedGfccsMetric
]

BASE_METRICS = {cls.name: cls for cls in _BASE_METRICS_LIST}
