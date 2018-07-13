
def to_db_column(metric):
    metrics = metric.split('_')
    if len(metrics) > 1:
        return 'array_cat({})'.format(', '.join(metrics))
    return metric
