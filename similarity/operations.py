import db.similarity


class Metric(object):
    name = ''
    description = ''
    category = ''

    def _create(self, hybrid, column):
        self.hybrid = str(hybrid).upper()
        db.similarity.insert_similarity_meta(self.name, hybrid, self.description, self.category)

    def delete(self):
        db.similarity.delete_similarity_meta(self.name)


class BaseMetric(Metric):
    def create(self, clear=False):
        db.similarity.create_similarity_metric(self.name, clear)
        self._create(hybrid=False, column=self.name)

    def delete(self, soft=False):
        if soft:
            db.similarity.remove_visibility(self.name)
        else:
            super(BaseMetric, self).delete()
            db.similarity.delete_similarity_metric(self.name)
