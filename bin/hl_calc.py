#!/usr/bin/env python

import sys
sys.path.append("../acousticbrainz")

import urllib2
import json
import os
from time import sleep
import subprocess
from operator import itemgetter
import psycopg2
import config
from threading import Thread
import random
from hashlib import sha256, sha1
from tempfile import NamedTemporaryFile, gettempdir, gettempprefix

MAX_THREADS = 4
HIGH_LEVEL_EXTRACTOR_BINARY = "streaming_extractor_music_svm"
PROFILE = "profile.conf"

class HighLevel(Thread):
    """
        This thread class calculates the high level data by calling the external high level calculator
    """

    def __init__(self, mbid, ll_data, ll_id):
        Thread.__init__(self)
        self.mbid = mbid
        self.ll_data = ll_data
        self.hl_data = None
        self.ll_id = ll_id

    def _calculate(self):
        """
           Invoke essentia high level extractor and return its JSON output
        """

        try:
            f = NamedTemporaryFile(delete=False)
            name = f.name
            f.write(self.ll_data)
            f.close()
        except IOError:
            return '{ "error" : "IO Error while writing temp file" }'

        out_file = os.path.join(gettempdir(), "%s-%d" % (gettempprefix(), os.getpid()))

        try:
            subprocess.check_call([os.path.join(".", HIGH_LEVEL_EXTRACTOR_BINARY), name, out_file, PROFILE])
        except subprocess.CalledProcessError:
            return '{ "error" : "Cannot call high level extractor" }'
            
        try:
            f = open(out_file)
            hl_data = f.read()
            f.close()
            os.unlink(out_file)
        except IOError:
            return '{ "error" : "IO Error while removing temp file" }'

        print hl_data

        return hl_data

    def get_data(self):
        return self.hl_data

    def get_ll_id(self):
        return self.ll_id

    def run(self):
        self.hl_data = self._calculate()

def get_documents(conn):
    """
        Fetch a number of low level documents to process from the DB
    """
    cur = conn.cursor()
    cur.execute("""SELECT ll.mbid, ll.data, ll.id
                     FROM lowlevel AS ll 
                LEFT JOIN highlevel AS hl 
                       ON ll.id = hl.id 
                    WHERE hl.mbid IS NULL
                    LIMIT 100""")
    return cur.fetchall()

def get_build_sha1(binary):
    """
        Calculate the sha1 of the binary we're using.
    """
    try:
        f = open(binary, "r")
        bin = f.read()
        f.close()
    except IOError:
        print "Cannot calculate the SHA256 of the high level binary"
        sys.exit(-1)

    return sha1(bin).hexdigest() 

build_sha1 = get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY)
conn = psycopg2.connect(config.PG_CONNECT)
num_processed = 0

pool = {}
docs = []
while True:

    # Check to see if we need more database rows
    if len(docs) == 0:
        # Fetch more rows from the DB
        docs = get_documents(conn)

        # We will fetch some rows that are already in progress. Remove those.
        in_progress = pool.keys()
        filtered = []
        for mbid, doc, id in docs:
            if not mbid in in_progress:
                filtered.append((mbid, doc, id))
        docs = filtered

    if len(docs):
        # Start one document
        mbid, doc, id = docs.pop()
        th = HighLevel(mbid, doc, id)
        th.start()
        print "start %s" % mbid
        pool[mbid] = th

    # If we're at max threads, wait for one to complete
    while True:
        if len(pool) == 0 and len(docs) == 0:
            print "processed %s documents, none remain." % num_processed
            sys.exit(0)

        for mbid in pool.keys():
            if not pool[mbid].is_alive():

                # Fetch the data and clean up the thread object
                hl_data = pool[mbid].get_data()
                ll_id = pool[mbid].get_ll_id()
                pool[mbid].join()
                del pool[mbid]

                # Calculate the sha for the data
                try:
                    jdata = json.loads(hl_data)
                except TypeError:
                    jdata = dict(error = "high level extractor produced bad JSON")

                sha = json.dumps(jdata, sort_keys=True, separators=(',', ':'))
                sha = sha256(sha).hexdigest()

                print "Cleaned up thread for %s" % mbid
                cur = conn.cursor()
                cur.execute("""INSERT INTO highlevel_json (data, data_sha256) 
                                    VALUES (%s, %s) 
                                 RETURNING id""", (hl_data, sha))
                id = cur.fetchone()[0]
                cur.execute("""INSERT INTO highlevel (id, mbid, build_sha1, data, submitted)
                                    VALUES (%s, %s, %s, %s, now())""", (ll_id, mbid, build_sha1, id))
                conn.commit()
                num_processed += 1

        if len(pool) == MAX_THREADS:
            # tranquilo!
            sleep(.1)
        else:
            break
