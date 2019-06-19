from sqlalchemy import text


class Metric(object):
    name = ''
    description = ''
    category = ''

    def __init__(self, connection):
        self.connection = connection

    def _create(self, hybrid, column):
        hybrid = str(hybrid).upper()
        metrics_query = text("""
            INSERT INTO similarity_metrics (metric, is_hybrid, description, category, visible)
                 VALUES (:metric, :hybrid, :description, :category, TRUE)
            ON CONFLICT (metric)
          DO UPDATE SET visible=TRUE
        """)
        self.connection.execute(metrics_query, {'metric': self.name,
                                                'hybrid': hybrid,
                                                'description': self.description,
                                                'category': self.category})

        # This can be removed if not using postgres similarity solution
        # index_query = text("""
        #     CREATE INDEX IF NOT EXISTS %(metric)s_ndx_similarity ON similarity
        #      USING gist(cube(%(column)s))
        # """ % {'metric': self.name, 'column': column})
        # self.connection.execute(index_query)

    def delete(self):
        metrics_query = text("""
            DELETE FROM similarity_metrics
                  WHERE metric = %s
        """ % self.name)
        self.connection.execute(metrics_query)

        # # This can be removed if not using postgres similarity solution
        # index_query = text("""
        #     DROP INDEX IF EXISTS %s_ndx_similarity
        # """ % self.name)
        # self.connection.execute(index_query)


class BaseMetric(Metric):
    def create(self, clear=False):
        query = text("""
            ALTER TABLE similarity
             ADD COLUMN
          IF NOT EXISTS %s DOUBLE PRECISION[]
        """ % self.name)
        self.connection.execute(query)
        self._create(hybrid=False, column=self.name)
        if clear:
            query = text("""
                UPDATE similarity
                   SET %(metric)s = NULL
            """ % {"metric": self.name})
            self.connection.execute(query)

    def delete(self, soft=False):
        if soft:
            query = text("""
                UPDATE similarity_metrics
                   SET visible = FALSE
                 WHERE metric = %s
            """ % self.name)
            self.connection.execute(query)
        else:
            super(BaseMetric, self).delete()
            query = text("""
                ALTER TABLE similarity
                DROP COLUMN
                  IF EXISTS %s
            """ % self.name)
            self.connection.execute(query)


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
            return ' || '.join(metrics)
        return metric
