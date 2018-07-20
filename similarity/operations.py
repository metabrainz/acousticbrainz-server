class Metric(object):
    name = ''
    description = ''
    category = ''

    def __init__(self, connection):
        self.connection = connection

    def _create(self, hybrid, column):
        hybrid = str(hybrid).upper()
        self.connection.execute("INSERT INTO similarity_metrics (metric, is_hybrid, description, category, visible) "
                                "VALUES ('%(metric)s', %(hybrid)s, '%(description)s', '%(category)s', TRUE) "
                                "ON CONFLICT DO NOTHING"
                                % {'metric': self.name, 'hybrid': hybrid, 'description': self.description,
                                   'category': self.category})
        self.connection.execute("CREATE INDEX IF NOT EXISTS %(metric)s_ndx_similarity ON similarity "
                                "USING gist(cube(%(column)s))" % {'metric': self.name, 'column': column})

    def delete(self):
        self.connection.execute("DELETE FROM similarity_metrics WHERE metric='%s'" % self.name)
        self.connection.execute("DROP INDEX IF EXISTS %s_ndx_similarity" % self.name)


class BaseMetric(Metric):
    def create(self, clear=False):
        self._create(hybrid=False, column=self.name)
        self.connection.execute("ALTER TABLE similarity ADD COLUMN IF NOT EXISTS %s DOUBLE PRECISION[]" % self.name)
        if clear:
            self.connection.execute("UPDATE similarity SET %s = NULL" % self.name)

    def delete(self, soft=False):
        super(BaseMetric, self).delete()

        if not soft:
            self.connection.execute("ALTER TABLE similarity DROP COLUMN IF EXISTS %s " % self.name)


class HybridMetric(Metric):
    def __init__(self, connection, name, category=None, description=None):
        super(HybridMetric, self).__init__(connection)
        self.name = name
        self.category = category
        self.description = description
        self.index_name = 'hybrid_%s_ndx_similarity' % name
        self.pseudo_column = self.get_pseudo_column(name)

        # TODO: automatic inferring of category and description

    def create(self):
        if not self.category or not self.description:
            raise ValueError('Category and description are required for creating new hybrid metric')
        column = self.get_pseudo_column(self.name)
        self._create(hybrid=True, column=column)

    @staticmethod
    def get_pseudo_column(metric):
        metrics = metric.split('_')
        if len(metrics) > 1:
            return 'array_cat({})'.format(', '.join(metrics))
        return metric
