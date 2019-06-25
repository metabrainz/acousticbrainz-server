import db
from operations import HybridMetric
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
    with db.engine.connect() as connection:
        index = AnnoyModel(connection, metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
        return index


# Postgres method
def get_similar_recordings(mbid, metric, limit=QUERY_RESULT_SIZE):
    with db.engine.begin() as connection:
        # check both existence and if it is hybrid
        # TODO (refactor): separate metric info from similarity
        result = connection.execute("SELECT is_hybrid, category, description FROM similarity_metrics WHERE metric='%s'" % metric)
        row = result.fetchone()
        if not row:
            return None

        # translate metric name to array_cat expression if hybrid
        is_hybrid, category, description = row
        metric = HybridMetric.get_pseudo_column(metric) if is_hybrid else metric

        # actual query
        result = connection.execute("""
            SELECT
              gid, submission_offset
            FROM lowlevel
            JOIN similarity ON lowlevel.id = similarity.id
            WHERE gid != '%(gid)s'
            ORDER BY cube(%(metric)s) <-> cube((
                SELECT %(metric)s
                FROM similarity
                JOIN lowlevel on similarity.id = lowlevel.id
                WHERE lowlevel.gid='%(gid)s'
                LIMIT 1
              ))
            LIMIT %(max)s
        """ % {'metric': metric, 'gid': mbid, 'max': limit})
        recordings = []
        for row in result.fetchall():
            recordings.append((row["gid"], row["submission_offset"]))

        return recordings, category, description
