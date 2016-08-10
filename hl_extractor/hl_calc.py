#!/usr/bin/env python
from __future__ import print_function
from hashlib import sha256, sha1
from threading import Thread
from time import sleep
import utils.hl_calc
import subprocess
import tempfile
import argparse
import json
import yaml
import os
from setproctitle import setproctitle

# Configuration
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

import db.data
import db
import config

DEFAULT_NUM_THREADS = 1

SLEEP_DURATION = 30  # number of seconds to wait between runs
HIGH_LEVEL_EXTRACTOR_BINARY = "streaming_extractor_music_svm"

PROFILE_CONF_TEMPLATE = "profile.conf.in"
PROFILE_CONF = "profile.conf"


class HighLevel(Thread):
    """This thread class calculates the high-level data by calling the external
    high-level calculator.
    """

    def __init__(self, mbid, ll_data, ll_id):
        Thread.__init__(self)
        self.mbid = mbid
        self.ll_data = ll_data
        self.hl_data = None
        self.ll_id = ll_id

    def _calculate(self):
        """Invoke Essentia high-level extractor and return its JSON output."""

        try:
            f = tempfile.NamedTemporaryFile(delete=False)
            name = f.name
            f.write(self.ll_data.encode("utf-8"))
            f.close()
        except IOError:
            print("IO Error while writing temp file")
            # If we return early, remove the ll file we created
            os.unlink(name)
            return "{}"

        # Securely generate a temporary filename
        tmp_file = tempfile.mkstemp()
        out_file = tmp_file[1]
        os.close(tmp_file[0])

        fnull = open(os.devnull, 'w')
        try:
            subprocess.check_call([os.path.join(".", HIGH_LEVEL_EXTRACTOR_BINARY),
                                   name, out_file, PROFILE_CONF],
                                  stdout=fnull, stderr=fnull)
        except (subprocess.CalledProcessError, OSError):
            print("Cannot call high-level extractor")
            # If we return early, make sure we remove the temp
            # output file that we created
            os.unlink(out_file)
            return "{}"
        finally:
            # At this point we can remove the source file,
            # regardless of if we failed or if we succeeded
            fnull.close()
            os.unlink(name)

        try:
            f = open(out_file)
            hl_data = f.read()
            f.close()
        except IOError:
            print("IO Error while removing temp file")
            return "{}"
        finally:
            os.unlink(out_file)

        return hl_data

    def get_data(self):
        return self.hl_data

    def get_ll_id(self):
        return self.ll_id

    def run(self):
        self.hl_data = self._calculate()


def main(num_threads):
    print("High-level extractor daemon starting with %d threads" % num_threads)
    sys.stdout.flush()
    build_sha1 = utils.hl_calc.get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY)
    utils.hl_calc.create_profile(PROFILE_CONF_TEMPLATE, PROFILE_CONF, build_sha1)
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)

    num_processed = 0

    pool = {}
    docs = []
    while True:
        # Check to see if we need more database rows
        if len(docs) == 0:
            # Fetch more rows from the DB
            docs = db.data.get_unprocessed_highlevel_documents()

            # We will fetch some rows that are already in progress. Remove those.
            in_progress = pool.keys()
            filtered = []
            for mbid, doc, id in docs:
                if mbid not in in_progress:
                    filtered.append((mbid, doc, id))
            docs = filtered

        if len(docs):
            # Start one document
            mbid, doc, id = docs.pop()
            th = HighLevel(mbid, doc, id)
            th.start()
            print("start %s" % mbid)
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
                # TODO: Close connections when we're sleeping
                sleep(SLEEP_DURATION)

            for mbid in pool.keys():
                if not pool[mbid].is_alive():

                    # Fetch the data and clean up the thread object
                    hl_data = pool[mbid].get_data()
                    ll_id = pool[mbid].get_ll_id()
                    pool[mbid].join()
                    del pool[mbid]

                    try:
                        jdata = json.loads(hl_data)
                    except ValueError:
                        print("error %s: Cannot parse result document" % mbid)
                        print(hl_data)
                        sys.stdout.flush()
                        jdata = {}

                    db.data.write_high_level(mbid, ll_id, jdata, build_sha1)

                    print("done  %s" % mbid)
                    sys.stdout.flush()
                    num_processed += 1

            if len(pool) == num_threads:
                # tranquilo!
                sleep(.1)
            else:
                break

if __name__ == "__main__":
    setproctitle("hl_calc")
    parser = argparse.ArgumentParser(description='Extract high-level data from low-level data')
    parser.add_argument("-t", "--threads", help="Number of threads to start", default=DEFAULT_NUM_THREADS, type=int)
    args = parser.parse_args()
    main(args.threads)
