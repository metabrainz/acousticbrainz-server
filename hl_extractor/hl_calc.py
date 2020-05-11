#!/usr/bin/env python
from __future__ import print_function

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from time import sleep

import concurrent.futures
import yaml

import db
import db.data

DEFAULT_NUM_THREADS = 1

SLEEP_DURATION = 30  # number of seconds to wait between runs
BASE_DIR = os.path.dirname(__file__)
BIN_PATH = "/usr/local/bin"
HIGH_LEVEL_EXTRACTOR_BINARY = os.path.join(BIN_PATH, "essentia_streaming_extractor_music_svm")

PROFILE_CONF_TEMPLATE = os.path.join(BASE_DIR, "profile.conf.in")
PROFILE_CONF = os.path.join(BASE_DIR, "profile.conf")

DOCUMENTS_PER_QUERY = 100


def process_mbid(mbid, ll_data):
    print("Starting {}".format(mbid))
    try:
        f = tempfile.NamedTemporaryFile(delete=False)
        name = f.name
        f.write(ll_data.encode("utf-8"))
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
        subprocess.check_call([HIGH_LEVEL_EXTRACTOR_BINARY,
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
        with open(out_file) as fp:
            hl_data = fp.read()
    except IOError:
        print("IO Error while reading temp file")
        return "{}"
    finally:
        os.unlink(out_file)

    print("Finished {}".format(mbid))
    return hl_data


def create_profile(in_file, out_file, sha1):
    """Prepare a profile file for use with essentia. Sanity check to make sure
    important values are present.
    """

    try:
        with open(in_file, 'r') as f:
            doc = yaml.load(f, Loader=yaml.SafeLoader)
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

    try:
        with open(out_file, 'w') as yaml_file:
            yaml.dump(doc, yaml_file, default_flow_style=False)
    except IOError as e:
        print("Cannot write profile %s: %s" % (out_file, e))
        sys.exit(-1)


def get_build_sha1(binary):
    """Calculate the SHA1 of the binary we're using."""
    try:
        with open(binary, "rb") as fp:
            contents = fp.read()
    except IOError as e:
        print("Cannot calculate the SHA1 of the high-level extractor binary: %s" % e)
        sys.exit(-1)

    return hashlib.sha1(contents).hexdigest()


def save_hl(mbid, rowid, hl_data, build_sha1):
    try:
        jdata = json.loads(hl_data)
    except ValueError:
        print("error %s: Cannot parse result document" % mbid)
        print(hl_data)
        jdata = {}

    db.data.write_high_level(mbid, rowid, jdata, build_sha1)


def cf_main(num_threads):
    print("High-level extractor daemon starting with %d threads" % num_threads)
    build_sha1 = get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY)
    create_profile(PROFILE_CONF_TEMPLATE, PROFILE_CONF, build_sha1)

    num_processed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        while True:
            docs = db.data.get_unprocessed_highlevel_documents(DOCUMENTS_PER_QUERY)
            print("Got %s documents" % len(docs))

            future_to_llid = {}
            for mbid, ll_json, rowid in docs:
                future_to_llid[executor.submit(process_mbid, mbid, ll_json)] = (rowid, mbid)

            for future in concurrent.futures.as_completed(future_to_llid):
                rowid, mbid = future_to_llid[future]
                try:
                    hl_data = future.result()
                except Exception as exc:
                    print('%r generated an exception: %s' % (mbid, exc))
                else:
                    num_processed += 1
                    save_hl(mbid, rowid, hl_data, build_sha1)

            # If we got less than the number of documents we asked for then we should wait
            # for a while for some more to appear
            if len(docs) < DOCUMENTS_PER_QUERY:
                if num_processed > 0:
                    print("processed %s documents, none remain. Sleeping." % num_processed)
                num_processed = 0
                sleep(SLEEP_DURATION)
