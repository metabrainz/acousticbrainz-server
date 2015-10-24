import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

import json
from sqlalchemy import text
import time
import logging
fmt = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)
import collections
import random

import db
import db.cache
import config

db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
db.cache.init(config.MEMCACHED_SERVERS)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def split_groundtruth(dataset):
    # the artists of each recording and make a training
    # set with only 1 recording of each artist and
    # a testing set with everything else

    # argument: a dataset from db.dataset.get
    # returns 2 dicts, trainset, testset of {recording: class}
    datadict = dataset_to_dict(dataset)
    
    recordingtoartists = {}
    recordings = datadict.keys()
    numrecordings = len(recordings)
    for recs in chunks(recordings, 1000):
        logging.info("Looking up 1000 artists")
        recarts = recordings_to_artists(recs)
        for r, a in recarts.items():
            if a:
                recordingtoartists[r] = a

    # Now that we have a map of recording -> artist,
    # randomly select items from the dataset and if we've
    # already selected the artist, put it in the test set

    classes = list(set(datadict.values()))
    artistinclass = {}
    for c in classes:
        artistinclass[c] = set()

    trainset = {}
    testset = {}
    for r in random.shuffle(recordings):
        cls = datadict[r]
        a = recordingtoartist[r]
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
           WHERE ll.mbid = :mbid""")
    result = db.engine.execute(q, {"mbid": mbid})
    row = result.fetchone()
    if row and row[0]:
	return row[0]
    else:
	return None

def recordings_to_artists(mbids):
    # First see if any ids are in memcache. If not, save them
    notincache = []
    ret = {}
    for m in mbids:
        a = db.cache.get(m, namespace='rectoartist')
        if a:
            ret[m] = a
        else:
            notincache.append(m)

    q = text(
       """SELECT mbid::text, data->'metadata'->'tags'->'musicbrainz_artistid'->>0
            FROM lowlevel ll
            JOIN lowlevel_json llj
 	      ON ll.id = llj.id
           WHERE ll.mbid in :mbids""")
    if notincache:
        print "Got", len(notincache), "not in cache"
        result = db.engine.execute(q, {"mbids": tuple(notincache)})
        for row in result.fetchall():
            if row[1]:
                db.cache.set(row[0], row[1], namespace='rectoartist')
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
