#!/usr/bin/env python
from __future__ import print_function

import argparse
import json
import os
import subprocess
import sys
import tempfile
from hashlib import sha1

from flask import current_app
from setproctitle import setproctitle
from threading import Thread
from time import sleep

import yaml

import db
import db.data
import db.dataset
import db.dataset_eval

DEFAULT_NUM_THREADS = 1

SLEEP_DURATION = 30  # number of seconds to wait between runs
BASE_DIR = os.path.dirname(__file__)
BIN_PATH = "/usr/local/bin"
HIGH_LEVEL_EXTRACTOR_BINARY = os.path.join(BIN_PATH, "essentia_streaming_extractor_music_svm")

PROFILE_CONF_TEMPLATE = os.path.join(BASE_DIR, "profile.conf.in")
PROFILE_CONF = os.path.join(BASE_DIR, "profile.conf")


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
            current_app.logger.error("IO Error while writing temp file")
            return "{}"

        # Securely generate a temporary filename
        tmp_file = tempfile.mkstemp()
        out_file = tmp_file[1]
        os.close(tmp_file[0])

        fnull = open(os.devnull, 'w')
        try:
            subprocess.check_call([HIGH_LEVEL_EXTRACTOR_BINARY,
                                   name, out_file, PROFILE_CONF],
                                  stdout=fnull, stderr=fnull)
        except subprocess.CalledProcessError:
            current_app.logger.error("Cannot call high-level extractor")
            return "{}"

        fnull.close()
        os.unlink(name)

        try:
            f = open(out_file)
            hl_data = f.read()
            f.close()
            os.unlink(out_file)
        except IOError:
            current_app.logger.error("IO Error while removing temp file")
            return "{}"

        return hl_data

    def get_data(self):
        return self.hl_data

    def get_ll_id(self):
        return self.ll_id

    def run(self):
        self.hl_data = self._calculate()


def create_profile(in_file, out_file, sha1):
    """Prepare a profile file for use with essentia. Sanity check to make sure
    important values are present.
    """

    try:
        with open(in_file, 'r') as f:
            doc = yaml.load(f, Loader=yaml.BaseLoader)
    except IOError as e:
        current_app.logger.error("Cannot read profile %s: %s" % (in_file, e))
        sys.exit(-1)

    try:
        models_ver = doc['mergeValues']['metadata']['version']['highlevel']['models_essentia_git_sha']
    except KeyError:
        models_ver = None

    if not models_ver:
        current_app.logger.warn("profile.conf.in needs to have 'metadata : version : highlevel :"
                                   " models_essentia_git_sha' defined.")
        sys.exit(-1)

    doc['mergeValues']['metadata']['version']['highlevel']['essentia_build_sha'] = sha1

    try:
        with open(out_file, 'w') as yaml_file:
            yaml_file.write( yaml.dump(doc, default_flow_style=False))
    except IOError as e:
        current_app.logger.error("Cannot write profile %s: %s" % (out_file, e))
        sys.exit(-1)


def get_build_sha1(binary):
    """Calculate the SHA1 of the binary we're using."""
    try:
        f = open(binary, "r")
        bin = f.read()
        f.close()
    except IOError as e:
        current_app.logger.error("Cannot calculate the SHA1 of the high-level extractor binary: %s" % e)
        sys.exit(-1)

    return sha1(bin).hexdigest()


def load_includes_from_eval(jobid):
    job = db.dataset_eval.get_job(jobid)
    test = db.dataset_eval.get_dataset_eval_set(job["testing_snapshot"])
    return test["data"].keys()


def get_model_from_eval(jobid):
    job = db.dataset_eval.get_job(jobid)
    dataset = db.dataset.get(job["dataset_id"])
    model_name = db.dataset.slugify(dataset["name"])
    model_version = "v1" # TODO: This has to be a parameter (from profile?)

    model_id = db.data._get_model_id(model_name, model_version)
    if model_id is None:
        model_id = db.data.add_model(model_name, model_version)

    return model_id


def main(num_threads, profile, dataset_job_id):
    current_app.logger.info("High-level extractor daemon starting with %d threads" % num_threads)
    sys.stdout.flush()
    build_sha1 = get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY)
    create_profile(profile, PROFILE_CONF, build_sha1)

    model_id = get_model_from_eval(dataset_job_id)
    includes = load_includes_from_eval(dataset_job_id)

    num_processed = 0

    pool = {}
    docs = []
    while True:
        # Check to see if we need more database rows
        if len(docs) == 0:
            # Fetch more rows from the DB
            docs = db.data.get_unprocessed_highlevel_documents_for_model(model_id, includes)

            # We will fetch some rows that are already in progress. Remove those.
            in_progress = pool.keys()
            filtered = []
            for mbid, doc, id in docs:
                if id not in in_progress:
                    filtered.append((mbid, doc, id))
            docs = filtered

        if len(docs):
            # Start one document
            mbid, doc, id = docs.pop()
            th = HighLevel(mbid, doc, id)
            th.start()
            current_app.logger.info("start %s" % id)
            sys.stdout.flush()
            pool[id] = th

        # If we're at max threads, wait for one to complete
        while True:
            if len(pool) == 0 and len(docs) == 0:
                if num_processed > 0:
                    current_app.logger.info("processed %s documents, none remain. Sleeping." % num_processed)
                    sys.stdout.flush()
                num_processed = 0
                # Let's be nice and not keep any connections to the DB open while we nap
                # TODO: Close connections when we're sleeping
                sleep(SLEEP_DURATION)

            for id in pool.keys():
                if not pool[id].is_alive():

                    # Fetch the data and clean up the thread object
                    hl_data = pool[id].get_data()
                    ll_id = pool[id].get_ll_id()
                    pool[id].join()
                    del pool[id]

                    try:
                        jdata = json.loads(hl_data)
                    except ValueError:
                        current_app.logger.error("error %s: Cannot parse result document" % mbid)
                        current_app.logger.error(hl_data)
                        sys.stdout.flush()
                        jdata = {}

                    db.data.write_high_level(mbid, ll_id, jdata, build_sha1)

                    current_app.logger.info("done  %s" % id)
                    sys.stdout.flush()
                    num_processed += 1

            if len(pool) == num_threads:
                # tranquilo!
                sleep(.1)
            else:
                break

if __name__ == "__main__":
    setproctitle("hl_calc")
    parser = argparse.ArgumentParser(description='Generate high-level data for a specific dataset evaluation process')
    parser.add_argument("-t", "--threads", help="Number of threads to start", default=DEFAULT_NUM_THREADS, type=int)
    parser.add_argument("profile", help="Profile file with highlevel models to generate", type=str)
    parser.add_argument("job", help="Job to evaluate", type=str)
    args = parser.parse_args()
    main(args.threads, args.profile, args.job)
