from __future__ import absolute_import
import gzip
import random
import math

import db.data
import db.exceptions
from similarity.index_model import AnnoyModel
import similarity.exceptions

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
# Percentage of a set of nearer neighbours that should be used
RANDOM_SAMPLE_SIZE = 0.7


def get_path(rec_1, rec_2, max_tracks, metric):
    # Get path between two recordings
    # Recording args in format (mbid, offset)
    n_tracks = 1
    no_gain_cnt = 0
    n_neighbours = INIT_N_NEIGHBOURS
    distances = []

    try:
        id_1 = db.data.get_lowlevel_id(rec_1[0], rec_1[1])
        id_2 = db.data.get_lowlevel_id(rec_2[0], rec_2[1])
    except db.exceptions.NoDataFoundException:
        raise similarity.exceptions.OdysseyException("The start/end MBID/Offset does not exist in the database.")

    try:
        index = AnnoyModel(metric, load_existing=True)
    except db.exceptions.NoDataFoundException:
        raise similarity.exceptions.OdysseyException("There are no recordings with computed similarity metrics.")
    except similarity.exceptions.ItemNotFoundException:
        raise similarity.exceptions.OdysseyException("No available index for the given metric and parameters.")

    init_distance = index.get_distance_between(id_1, id_2)
    if not init_distance:
        raise similarity.exceptions.OdysseyException("Annoy index is unable to compute distance between the given recorrdings.")
    path = [(rec_1[0], init_distance)]

    # nearest_rec = find_nearest_rec(id_1, id_2, init_distance, index, n_neighbours)
    nearest_id = id_1
    nearest_rec = (nearest_id, init_distance, rec_1)
    last_distance = init_distance

    # Checking to exit on max # tracks, if distance doesn't improve (3 times), 
    # or target is within nearest neighbours
    while n_tracks < max_tracks - 1 and no_gain_cnt < MAX_NO_GAIN:
        if nearest_rec:
            last_distance = nearest_rec[1]
            nearest_id = nearest_rec[0]
            nearest_rec = None

        nearer_recs = find_nearer_recs(nearest_id, id_2, rec_2, last_distance, index, n_neighbours)
        if not nearer_recs:
            n_neighbours = n_neighbours * 1.3
            no_gain_cnt += 1
        else:
            # Append nearest (MBID, offset) combination
            n_neighbours = INIT_N_NEIGHBOURS
            nearest_rec = nearer_recs[1]
            path += nearer_recs[0]

            # Remove duplicates in the nearest recordings
            seen = set()
            path = [x for x in path if not (x in seen or seen.add(x))]
            n_tracks = len(path)

    # print("LENGTH PATH {}".format(len(path)))
    # print("PATH")
    # print(path)
    # print("------------------------------")

    # Add last recording
    # if len(path) > max_tracks
    path += [[rec_2[0], 0]]
    # print("MAX {}".format(max_tracks))
    if len(path) > max_tracks:
        path = path[:max_tracks - 1] + [path[len(path) - 1]]

    print(len(path))
    return path



def get_path_debug(rec_1, rec_2):

    max_tracks = 100
    try:
        id_1 = db.data.get_lowlevel_id(rec_1[0], rec_1[1])
        id_2 = db.data.get_lowlevel_id(rec_2[0], rec_2[1])
    except db.exceptions.NoDataFoundException:
        raise similarity.exceptions.OdysseyException("The start/end MBID/Offset does not exist in the database.")

    init_distance = index.get_distance_between(id_1, id_2)
    if not init_distance:
        raise similarity.exceptions.OdysseyException("Annoy index is unable to compute distance between the given recorrdings.")

    results = {}
    results['distance'] = init_distance
    for metric in similarity.metrics.BASE_METRICS:
        results['tracks'][metric] = []

        try:
            indexes[metric] = AnnoyModel(metric, load_existing=True)
        except db.exceptions.NoDataFoundException:
            raise similarity.exceptions.OdysseyException("There are no recordings with computed similarity metrics.")
        except similarity.exceptions.ItemNotFoundException:
            raise similarity.exceptions.OdysseyException("No available index for the given metric and parameters.")

        try:
            n_ids, n_recs, n_distances = index.get_nns_by_id(rec_t[0], max_tracks)
        except similarity.exceptions.ItemNotFoundException:
            raise similarity.exceptions.OdysseyException("The id being queried was not found in the index.")

        for id, rec, dist in zip(n_ids, n_recs, n_distances):
            results['tracks'][metric].append((id, rec, dist))

    return jsonify(results)



# Find batch
# Assign nearest as the nearest distance and id as id_queried for next batch
# Add the nearest and a random subset of a percentage of the recordings
# Who are also nearer, but not as near as this
# Return nearer recs
# If id in list is the target id, return the list up to this point
# And finish by querying the target id for near recordings with another function
def find_nearer_recs(id_queried, id_target, rec_target, last_distance, index, n_neighbours):
    # Find recordings that will decrease the distance to the target
    try:
        n_ids, n_recs, n_distances = index.get_nns_by_id(id_queried, int(n_neighbours))
    except similarity.exceptions.ItemNotFoundException:
        raise similarity.exceptions.OdysseyException("The id being queried was not found in the index.")

    nearest_id = id_queried
    nearest_distance = last_distance
    nearer_ids = []
    nearer_recs = []
    nearer_distances = []
    for id, rec in zip(n_ids, n_recs):
        # If MBID matches target, skip (different submission)
        # If MBID and offset match target, exit
        if rec[0] == rec_target[0]:
            continue
        elif id == id_target:
            break

        new_distance = index.get_distance_between(id, id_target)
        if not new_distance:
            raise similarity.exceptions.OdysseyException("Annoy index is unable to compute distance between the given recorrdings.")

        if new_distance < last_distance:
            if new_distance < nearest_distance:
                nearest_id = id
                nearest_distance = new_distance
                nearest_mbid_offset = rec
            nearer_ids.append(id)
            nearer_recs.append(rec)
            nearer_distances.append(new_distance)
    
    # Remove offsets
    mbids = remove_offsets(nearer_recs)
    mbids_distances_sub = random.sample(zip(mbids, nearer_distances), int(math.ceil(len(nearer_recs)*RANDOM_SAMPLE_SIZE)))

    if nearest_distance == last_distance:
        return False

    return (mbids_distances_sub, (nearest_id, nearest_distance, nearest_mbid_offset))


def remove_offsets(recs):
    # Remove offsets from tuples, return only list of MBIDs
    mbids = [x[0] for x in recs]
    return mbids

# Planning how many nearer recs to take each time to fill a path
# Perhaps this should be experimentally determined:
# We can approximate the density,
# i.e. how far away is the nearest neighbour in the nearer direction?
# Can draw a circle which makes this the closest neighbour to the target
# Based on this density and the geometry of the section of the circle which
# approximates the location of similar recordings that are more near, we can
# use the overall distance between first and last recording to estimate how
# many recordings should be taken in each of the query cycles
# We can finish by removing recordings or adding nearby recordings to the
# target to reach the desired number of songs
# Possible advantageous to overestimate rather than underestimate and select
# nearby recordings to one position
def find_nearest_rec(id_queried, id_distance_to, last_distance, index, n_neighbours):
    # Find the nearest recording to an id
    try:
        n_ids, n_recs, n_distances = index.get_nns_by_id(id_queried, int(n_neighbours))
    except similarity.exceptions.ItemNotFoundException:
        raise similarity.exceptions.OdysseyException("The id being queried was not found in the index.")

    nearest_id = id_queried
    nearest_distance = last_distance
    for id, rec in zip(n_ids, n_recs):
        if id == id_distance_to:
            break

        new_distance = index.get_distance_between(id, id_distance_to)
        if not new_distance:
            raise similarity.exceptions.OdysseyException("Annoy index is unable to compute distance between the given recorrdings.")

        if new_distance < nearest_distance:
            nearest_id = id
            nearest_distance = new_distance
            nearest_mbid_offset = rec
    
    if nearest_distance == last_distance:
        return False
    return (nearest_id, nearest_distance, nearest_mbid_offset)
