import db
from index_model import AnnoyModel
import similarity.exceptions
import similarity.metrics

from collections import defaultdict

NORMALIZATION_SAMPLE_SIZE = 10000
PROCESS_BATCH_SIZE = 10000
QUERY_PADDING_FACTOR = 3
QUERY_RESULT_SIZE = 1000


def init_metrics():
    """Initializes and creates all base metrics, returning
    their instances as a list."""
    metrics = []
    for name in similarity.metrics.BASE_METRICS:
        metric_cls = similarity.metrics.BASE_METRICS[name]
        metric = metric_cls()
        metrics.append(metric)

    return metrics


def get_all_metrics():
    with db.engine.begin() as connection:
        result = connection.execute("""
            SELECT category, metric, description
            FROM similarity_metrics
            WHERE visible = TRUE
        """)

        metrics = {}
        for category, metric, description in result.fetchall():
            if category not in metrics:
                metrics[category] = []
            metrics[category].append([metric, description])

        return metrics


def get_all_indices(n_trees=10):
    distance_measures = [
        "angular",
        "manhattan"]
    metrics = ["mfccs",
               "mfccsw",
               "gfccs",
               "gfccsw",
               "key",
               "bpm",
               "onsetrate",
               "moods",
               "instruments",
               "dortmund",
               "rosamerica",
               "tzanetakis"]
    indices = defaultdict(list)
    for distance in distance_measures:
        for metric in metrics:
            indices[distance].append((metric, n_trees))
    return indices


def load_index_model(metric, n_trees=10, distance_type="angular"):
    index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
    return index


def remove_index(metric, n_trees=10, distance_type="angular"):
    file_path = os.path.join(os.getcwd(), 'annoy_indices')
    name = '_'.join([metric, distance_type, str(n_trees)]) + '.ann'
    full_path = os.path.join(file_path, name)
    if os.path.exists(full_path):
        os.remove(full_path)
