from __future__ import absolute_import

import collections
import json
import logging
import os
import random

from sqlalchemy import text

import db
import db.dataset
from utils.list_utils import chunks

fmt = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)

fname = "recordingtoartistmap.json"
if os.path.isfile(fname):
    rtoajson = json.load(open(fname))
else:
    rtoajson = {}


def print_datadict_summary(datadict):
    counter = collections.Counter()
    for r, cls in datadict.items():
        counter[cls] += 1
    for cls, count in counter.most_common():
        print "%s\t\t%s" % (cls, count)


def normalise_datadict(datadict, cut_to):
    """Take a dictionary of groundtruth and cut all classes to
    `cut_to` items. If a class has fewer items, discard it.
    Return newdatadict, removed where `removed` is a dictionary
    of items in datadict that haven't been added to newdatadict"""

    dataset = collections.defaultdict(list)
    for r, cls in datadict.items():
        dataset[cls].append(r)
    newdataset = {}
    remaining = {}
    for cls, items in dataset.items():
        if len(items) > cut_to:
            sample = random.sample(items, cut_to)
            for i in sample:
                newdataset[i] = cls
            rest = list(set(items)-set(sample))
            for i in rest:
                remaining[i] = cls
    return newdataset, remaining


def recordings_to_artists(recordings):
    recordingtoartist = {}
    numrecordings = len(recordings)
    for recs in chunks(recordings, 1000):
        recarts = recordings_to_artists_sub(recs)
        for r, a in recarts.items():
            if a:
                recordingtoartist[r] = a
    return recordingtoartist


def filter(snapshot_id, options):
    snapshot = db.dataset.get_snapshot(snapshot_id)
    datadict = dataset_to_dict(snapshot["data"])
    if options.get("filter_type") == "artist":
        print ("Filtering by artist")
        train, test = split_groundtruth(datadict)
    else:
        train = datadict
        test = {}
    if options.get("normalize"):
        print("Normalising")
        train, remaining = normalise_datadict(train, 450)
        test.update(remaining)

    return train, test


def split_groundtruth(datadict):
    # the artists of each recording and make a training
    # set with only 1 recording of each artist and
    # a testing set with everything else

    # argument: a dataset from db.dataset.get
    # returns 2 dicts, trainset, testset of {recording: class}
    recordings = datadict.keys()
    recordingtoartist = recordings_to_artists(recordings)

    # Now that we have a map of recording -> artist,
    # randomly select items from the dataset and if we've
    # already selected the artist, put it in the test set

    classes = list(set(datadict.values()))
    artistinclass = {}
    for c in classes:
        artistinclass[c] = set()

    trainset = {}
    testset = {}
    reclist = [r for r in recordings]
    random.shuffle(reclist)
    for r in reclist:
        cls = datadict[r]
        a = recordingtoartist.get(r)
        if a:
            if a in artistinclass[cls]:
                testset[r] = cls
            else:
                trainset[r] = cls
            artistinclass[cls].add(a)

    #TODO If the test set doesn't have enough samples, take from
    # test (how many? 20%?)
    # TODO: if requested, chop the size of the classes to be the same
    # TODO: if one class is too small (1000?) we will make all of them
    # small, consider removing this class
    return trainset, testset


def recording_to_artist(mbid):
    q = text(
       """SELECT data->'metadata'->'tags'->'musicbrainz_artistid'->>0
            FROM lowlevel ll
            JOIN lowlevel_json llj
           ON ll.id = llj.id
           WHERE ll.gid = :mbid""")
    result = db.engine.execute(q, {"mbid": mbid})
    row = result.fetchone()
    if row and row[0]:
        return row[0]
    else:
        return None


def recordings_to_artists_sub(mbids):
    # First see if any ids are in memcache. If not, save them
    notincache = []
    ret = {}
    for m in mbids:
        a = rtoajson.get(m)
        if a:
            ret[m] = a
        else:
            notincache.append(m)

    q = text(
       """SELECT gid::text, data->'metadata'->'tags'->'musicbrainz_artistid'->>0
            FROM lowlevel ll
            JOIN lowlevel_json llj
              ON ll.id = llj.id
           WHERE ll.gid in :mbids""")
    if notincache:
        result = db.engine.execute(q, {"mbids": tuple(notincache)})
        for row in result.fetchall():
            ret[row[0]] = row[1]
    return ret


def dataset_to_dict(ds):
    # Convert an acousticbrainz dataset from `db.dataset.get` to a simple
    # dictionary of {instance: class, i2: c2}
    data = {}
    for c in ds["classes"]:
        for r in c["recordings"]:
            data[r] = c["name"]
    return data
