#!/usr/bin/env python
from __future__ import print_function
from hashlib import sha256, sha1
from threading import Thread
from time import sleep
import subprocess
import psycopg2
import tempfile
import argparse
import json
import yaml
import os
from setproctitle import setproctitle

# Importing AcousticBrainz config file
import sys
sys.path.append("../acousticbrainz")
import config

DEFAULT_NUM_THREADS = 1

FILES_PER_BINARY = 5

SLEEP_DURATION = 30  # number of seconds to wait between runs
HIGH_LEVEL_EXTRACTOR_BINARY = "streaming_extractor_music_svm"

class HighLevel(Thread):
    """This thread class calculates the high-level data by calling the external
    high-level calculator.
    """

    def __init__(self, input_data, profile_file):
        Thread.__init__(self)
        # (mbid, ll_data, ll_id)
        self.input_data = input_data
        # (mbid, ll_id, hl_data)
        self.output_data = []
        self.profile_file = profile_file

    def _calculate(self):
        """Invoke Essentia high-level extractor and return its JSON output."""

        in_out_args = []
        idfnames = []
        for mbid, ll_data, ll_id in self.input_data:
            try:
                f = tempfile.NamedTemporaryFile(delete=False)
                name = f.name
                f.write(ll_data)
                f.close()
            except IOError:
                print("IO Error while writing temp file")
                return "{}"

            # Securely generate a temporary filename
            tmp_file = tempfile.mkstemp()
            out_file = tmp_file[1]
            os.close(tmp_file[0])

            in_out_args.append(name)
            in_out_args.append(out_file)
            idfnames.append( (mbid, ll_id, name, out_file) )

        fnull = open(os.devnull, 'w')
        try:
            subprocess.check_call([os.path.join(".", HIGH_LEVEL_EXTRACTOR_BINARY)] +
                    in_out_args + [self.profile_file],
                                  stdout=fnull, stderr=fnull)
        except subprocess.CalledProcessError:
            print("Cannot call high-level extractor")
            return []

        fnull.close()

        all_data = []
        for mbid, ll_id, name, out_file in idfnames:
            os.unlink(name)

            try:
                f = open(out_file)
                hl_data = f.read()
                f.close()
                os.unlink(out_file)
            except IOError:
                print("IO Error while removing temp file")
                continue

            all_data.append( (mbid, ll_id, hl_data) )

        return all_data

    def get_all_data(self):
        return self.output_data

    def run(self):
        self.output_data = self._calculate()


def get_documents(conn, hlname):
    """Fetch a number of low-level documents to process from the DB."""
    cur = conn.cursor()
    duplimit = "INNER JOIN d2mbids on d2mbids.mbid=ll.mbid"
    duplimit = ""
    hl_get = """SELECT ll.mbid, ll.data::text, ll.id
                     FROM lowlevel AS ll
                LEFT JOIN %s AS hl
                       ON ll.id = hl.id
                       %s
                    WHERE hl.mbid IS NULL
                    LIMIT 1000""" % (hlname, duplimit)
    cur.execute(hl_get)
    docs = cur.fetchall()
    cur.close()
    return docs


def create_profile(in_file, sha1):
    """Prepare a profile file for use with essentia. Sanity check to make sure
    important values are present.
    """
    assert(in_file.endswith(".in"))

    try:
        with open(in_file, 'r') as f:
            doc = yaml.load(f)
    except IOError as e:
        print("Cannot read profile %s: %s" % (in_file, e))
        sys.exit(-1)

    try:
        models_ver = doc['mergeValues']['metadata']['version']['highlevel']['models_essentia_git_sha']
    except KeyError:
        models_ver = None

    if not models_ver:
        print("profile.conf.in needs to have 'metadata : version : highlevel :"
              " models_essentia_git_sha' defined.")
        sys.exit(-1)

    doc['mergeValues']['metadata']['version']['highlevel']['essentia_build_sha'] = sha1

    out_file = in_file.replace(".in", "")
    try:
        with open(out_file, 'w') as yaml_file:
            yaml_file.write( yaml.dump(doc, default_flow_style=False))
            return yaml_file.name
    except IOError as e:
        print("Cannot write profile %s: %s" % (out_file, e))
        sys.exit(-1)


def get_build_sha1(binary):
    """Calculate the SHA1 of the binary we're using."""
    try:
        f = open(binary, "r")
        bin = f.read()
        f.close()
    except IOError as e:
        print("Cannot calculate the SHA1 of the high-level extractor binary: %s" % e)
        sys.exit(-1)

    return sha1(bin).hexdigest()

def add_to_database(conn, hlname, data, build_sha1):
    # Calculate the sha for the data

    if not conn:
        conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    for mbid, ll_id, hl_data in data:
        try:
            jdata = json.loads(hl_data)
        except ValueError:
            print("error %s: Cannot parse result document" % mbid)
            print(hl_data)
            sys.stdout.flush()
            jdata = {}

        norm_data = json.dumps(jdata, sort_keys=True, separators=(',', ':'))
        sha = sha256(norm_data).hexdigest()

        print("done  %s" % mbid)
        sys.stdout.flush()

        hl_json_insert = """INSERT INTO %s_json (data, data_sha256)
                            VALUES (%%s, %%s)
                         RETURNING id""" % hlname
        cur.execute(hl_json_insert, (norm_data, sha))
        id = cur.fetchone()[0]
        hl_insert = """INSERT INTO %s (id, mbid, build_sha1, data, submitted)
                            VALUES (%%s, %%s, %%s, %%s, now())""" % hlname
        cur.execute(hl_insert, (ll_id, mbid, build_sha1, id))

    # only commit after all the data is done
    conn.commit()


def main(num_threads, hlname, profile_template):
    print("High-level extractor daemon starting with %d threads" % num_threads)
    sys.stdout.flush()
    build_sha1 = get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY)
    profile = create_profile(profile_template, build_sha1)

    conn = None
    num_processed = 0

    pool = {}
    in_progress = set()
    docs = []
    while True:
        # Check to see if we need more database rows
        if len(docs) < FILES_PER_BINARY:
            # Fetch more rows from the DB
            if not conn:
                conn = psycopg2.connect(config.PG_CONNECT)
            docs = get_documents(conn, hlname)

            # We will fetch some rows that are already in progress. Remove those.
            filtered = []
            for mbid, doc, id in docs:
                if mbid not in in_progress:
                    filtered.append((mbid, doc, id))
            docs = filtered

        print("remaining %s docs" % len(docs))
        if len(docs):
            # Start up to FILES_PER_BINARY documents
            thisthread = []
            for i in range(FILES_PER_BINARY):
                mbid, ll_data, ll_id = docs.pop()
                thisthread.append( (mbid, ll_data, ll_id) )
                in_progress.add(mbid)
                if not docs:
                    break
            print ("starting thread with %s" % len(thisthread))
            th = HighLevel(thisthread, profile)
            th.start()
            mbid = thisthread[0][0]
            print("start %s - plus %s more" % (mbid, len(thisthread)-1))
            sys.stdout.flush()
            pool[mbid] = th

        # If we're at max threads, wait for one to complete
        while True:
            if len(pool) == 0 and len(docs) == 0:
                if num_processed > 0:
                    print("processed %s documents, none remain. Sleeping." % num_processed)
                    sys.stdout.flush()
                num_processed = 0
                # Let's be nice and not keep any connections to the DB open while we nap
                conn.close()
                conn = None
                sleep(SLEEP_DURATION)

            for mbid in pool.keys():
                if not pool[mbid].is_alive():

                    # Fetch the data and clean up the thread object
                    data = pool[mbid].get_all_data()
                    pool[mbid].join()
                    del pool[mbid]

                    add_to_database(conn, hlname, data, build_sha1)
                    # remove from in progress
                    for mbid, ll_id, hl_doc in data:
                        in_progress.remove(mbid)

                    num_processed += len(data)

            if len(pool) == num_threads:
                # tranquilo!
                sleep(.1)
            else:
                break

if __name__ == "__main__":
    setproctitle("hl_calc")
    parser = argparse.ArgumentParser(description='Extract high-level data from low-level data')
    parser.add_argument("-t", "--threads", help="Number of threads to start", default=DEFAULT_NUM_THREADS, type=int)
    parser.add_argument("hlname", help="Name of highlevel table")
    parser.add_argument("profile", help="name of profile.in file with models")
    args = parser.parse_args()
    main(args.threads, args.hlname, args.profile)
