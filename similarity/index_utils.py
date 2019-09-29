import os

import similarity.metrics
from similarity.index_model import AnnoyModel

from collections import defaultdict


def get_all_indices(n_trees=10):
    """Returns a dictionary of the indices that must be built for the
    specified distance measures and metrics"""
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


def initialize_indices(n_trees="10", distance_type="angular", load_existing=False):
    """Initializes indices for all base metrics, appending them 
    to a list which is returned."""
    indices = []
    for name in similarity.metrics.BASE_METRICS:
        index = AnnoyModel(name, n_trees=n_trees, distance_type=distance_type, load_existing=load_existing)
        indices.append(index)
    return indices


def remove_index(metric, n_trees=10, distance_type="angular"):
    """Deletes the static index originally saved when an index is computed."""
    file_path = os.path.join(os.getcwd(), 'annoy_indices')
    name = '_'.join([metric, distance_type, str(n_trees)]) + '.ann'
    full_path = os.path.join(file_path, name)
    if os.path.exists(full_path):
        os.remove(full_path)


def get_similar_recordings(metric, mbid, offset, distance_type="angular", n_trees=10, n_neighbours=200):
    # Initializes index with given params, and calls for similar recordings.
    index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
    similar_recordings = index.get_nns_by_mbid(str(mbid), offset, n_neighbours)


def add_empty_rows(index, ids):
    """Annoy index will allocate space for max(id) + 1 items.
    Since there are some gaps with empty rows in the db, we
    need to insert placeholder vectors so that Annoy does
    not initialize unpredictable vectors in their place.

    Args:
        index: An initialized Annoy index.

        ids (list): A list of ids which should be added to the index.
        Will be used to find empty rows.
    """
    missing_ids = set(range(ids[len(ids)-1])) - set(ids)
    for id in missing_ids:
        placeholder = [0] * index.dimension
        index.add_recording_with_vector(id, placeholder)
    return index
