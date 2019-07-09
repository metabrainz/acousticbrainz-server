import similarity.metrics


def init_metrics(force=False):
    """Initializes and creates all base metrics, returning
    their instances as a list."""
    metrics = []
    for name in similarity.metrics.BASE_METRICS:
        metric_cls = similarity.metrics.BASE_METRICS[name]
        metric = metric_cls()
        metric.create(clear=force)
        metrics.append(metric)
        try:
            metric.calculate_stats()
        except AttributeError:
            pass
    return metrics
