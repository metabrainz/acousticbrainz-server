import db
from index_model import AnnoyModel
import similarity.exceptions
import similarity.metrics

from collections import defaultdict
from sqlalchemy import text

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


def add_index(metric, batch_size=None, n_trees=10, distance_type='angular'):
    """Creates an annoy index for the specified metric, adds all items to the index."""
    print("Initializing index...")
    index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type)

    batch_size = batch_size or PROCESS_BATCH_SIZE
    offset = 0
    count = 0

    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT MAX(id)
              FROM similarity
        """)
        total = result.fetchone()[0]

        batch_query = text("""
            SELECT *
              FROM similarity
             ORDER BY id
             LIMIT :batch_size
            OFFSET :offset
        """)

        print("Inserting items...")
        while True:
            # Get ids and vectors for specific metric in batches
            batch_result = connection.execute(batch_query, { "batch_size": batch_size, "offset": offset })
            if not batch_result.rowcount:
                print("Finished adding items. Building index...")
                break

            for row in batch_result.fetchall():
                while not row["id"] == count:
                    # Rows are empty, add zero vector
                    placeholder = [0] * index.dimension
                    index.add_recording_with_vector(count, placeholder)
                    count += 1
                index.add_recording_with_vector(row["id"], row[index.metric_name])
                count += 1

            offset += batch_size
            print("Items added: {}/{} ({:.3f}%)".format(offset, total, float(offset) / total * 100))

        index.build()
        print("Saving index...")
        index.save()


def remove_index(metric, n_trees=10, distance_type="angular"):
    file_path = os.path.join(os.getcwd(), 'annoy_indices')
    name = '_'.join([metric, distance_type, str(n_trees)]) + '.ann'
    full_path = os.path.join(file_path, name)
    if os.path.exists(full_path):
        os.remove(full_path)
