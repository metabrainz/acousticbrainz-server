from __future__ import absolute_import
import gzip

import db.data
from similarity.index_model import AnnoyModel

##### Option 1 #####
# Pick a song to start.
# Pick a song to finish.
# ** For now, pick a metric to go by **
# Query Annoy for distance between the two songs
# Query Annoy for similar recordings to the first song, in terms of that metric
# Search for similar recording, then query for distance between this recording and the final recording
# Pick similar recording that reduces distance
# Repeat with this as the starting song

# Max number of steps without decreasing distance before program exits
MAX_NO_GAIN = 3
INIT_N_NEIGHBOURS = 55


def get_path(rec_1, rec_2, max_tracks, metric):
    # Get path between two recordings
    # Recording args in format (mbid, offset)
    id_1 = db.data.get_lowlevel_id(rec_1[0], rec_1[1])
    id_2 = db.data.get_lowlevel_id(rec_2[0], rec_2[1])
    index = AnnoyModel(metric, load_existing=True)
    n_tracks = 0
    no_gain_cnt = 0
    n_neighbours = INIT_N_NEIGHBOURS
    distances = []
    path = []
    init_distance = index.get_distance_between(id_1, id_2)
    nearest_rec = find_nearest_rec(id_1, id_2, init_distance, index, n_neighbours)
    nearest_id = id_1
    last_distance = init_distance

    # Checking to exit on max # tracks, if distance doesn't improve (3 times), 
    # or target is within nearest neighbours
    while n_tracks < max_tracks and no_gain_cnt < MAX_NO_GAIN:
        if nearest_rec:
            last_distance = nearest_rec[1]
            nearest_id = nearest_rec[0]
            nearest_rec = None

        nearest_rec = find_nearest_rec(nearest_id, id_2, last_distance, index, n_neighbours)
        if not nearest_rec:
            n_neighbours = n_neighbours * 2
            no_gain_cnt += 1
        else:
            # Append nearest (MBID, offset) combination
            n_neighbours = INIT_N_NEIGHBOURS
            path.append(nearest_rec[2])
            distances.append(last_distance)
            n_tracks += 1

    distances = [init_distance] + distances
    path = [rec_1] + path + [rec_2]
    return path, distances


def find_nearest_rec(id_queried, id_distance_to, last_distance, index, n_neighbours):
    # Find the nearest recording to an id
    n_ids, n_recs, n_distances = index.get_nns_by_id(id_queried, int(n_neighbours))
    nearest_id = id_queried
    nearest_distance = last_distance
    for id, rec in zip(n_ids, n_recs):
        if id == id_distance_to:
            break
        new_distance = index.get_distance_between(id, id_distance_to)
        if new_distance < nearest_distance:
            nearest_id = id
            nearest_distance = new_distance
            nearest_mbid_offset = rec
    
    if nearest_distance == last_distance:
        return False
    return (nearest_id, nearest_distance, nearest_mbid_offset)
