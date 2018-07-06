import numpy as np

SAMPLE_SIZE = 10000


class Metric(object):
    name = ''
    description = ''

    def is_present(self):
        pass


class LowLevelMetric(Metric):
    path = ''
    indices = None

    def get_data(self, connection, ids):
        result = connection.execute("SELECT id, %(path)s FROM lowlevel_json WHERE id IN %(ids)s" %
                                    {'ids': str(ids), 'path': self.path})
        return result.fetchall()


class NormalizedLowLevelMetric(LowLevelMetric):
    means = None
    stddevs = None

    def calculate_stats(self, connection):
        result = connection.execute("SELECT means, stddevs FROM similarity_stats WHERE metric='%s'" % self.name)
        row = result.fetchone()

        if row:
            print('Global stats already calculated')
            self.means, self.stddevs = row
            return

        print('Calculating global stats for {}'.format(self.name))
        self.means = []
        self.stddevs = []
        for i in self.indices:  # TODO: make it work with single values
            print('Index {} (out of {})'.format(i, len(self.indices)))
            result = connection.execute("SELECT avg(x), stddev_pop(x)"
                                        "FROM (SELECT (%(field)s->>%(i)s)::double precision as x "
                                        "FROM lowlevel_json "
                                        "LIMIT %(limit)s) as res" %
                                        {'field': self.path, 'i': i, 'limit': SAMPLE_SIZE})
            mean, stddev = result.fetchone()
            self.means.append(mean)
            self.stddevs.append(stddev)

        connection.execute("INSERT INTO similarity_stats (metric, means, stddevs) "
                           "VALUES (%(metric)s, %(means)s, %(stddevs)s)"
                           % {'metric': "'{}'".format(self.name),
                              'means': 'ARRAY' + str(self.means),
                              'stddevs': 'ARRAY' + str(self.stddevs)})

    def delete_stats(self, connection):
        print('Deleting global stats')
        connection.execute("DELETE FROM similarity_stats WHERE metric='%s'" % self.name)

    def get_data(self, connection, ids):
        data = super(NormalizedLowLevelMetric, self).get_data(connection, ids)

        # Normalize
        data = np.array(data)[self.indices]
        return (data - np.array(self.means)) / np.array(self.stddevs)


class WeightedNormalizedLowLevelMetric(NormalizedLowLevelMetric):
    weight = 0.95

    def __init__(self):
        super(WeightedNormalizedLowLevelMetric, self).__init__()
        self.weight_vector = np.array([])

    def get_data(self, connection, ids):
        data = super(WeightedNormalizedLowLevelMetric, self).get_data(connection, ids)



class MfccsMetric(NormalizedLowLevelMetric):
    name = 'mfccs'
    description = 'MFCCs'
    path = "data->'lowlevel'->'mfcc'->'mean'"
    indices = range(1, 13)


class MfccsMetric(NormalizedLowLevelMetric):
    name = 'mfccs'
    description = 'MFCCs'
    path = "data->'lowlevel'->'mfcc'->'mean'"
    indices = range(1, 13)


class MfccsMetric(NormalizedLowLevelMetric):
    name = 'mfccs'
    description = 'MFCCs'
    path = "data->'lowlevel'->'mfcc'->'mean'"
    indices = range(1, 13)


class MfccsMetric(NormalizedLowLevelMetric):
    name = 'mfccs'
    description = 'MFCCs'
    path = "data->'lowlevel'->'mfcc'->'mean'"
    indices = range(1, 13)


class HighLevelMetric(Metric):
    @classmethod
    def get_data(cls, connection, ids):
        result = connection.execute("SELECT highlevel, jsonb_object_agg(model, data) "
                                    "FROM highlevel_model WHERE highlevel IN %s "
                                    "GROUP BY highlevel" % str(ids))
        return result.fetchall()
