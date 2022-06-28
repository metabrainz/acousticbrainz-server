#!/usr/bin/env python
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import concurrent.futures
import yaml
from flask import current_app

import db
import db.data

DEFAULT_NUM_THREADS = 2

SLEEP_DURATION = 30  # number of seconds to wait between runs
BASE_DIR = os.path.dirname(__file__)
BIN_PATH = "/usr/local/bin"
HIGH_LEVEL_EXTRACTOR_BINARY = os.path.join(BIN_PATH, "essentia_streaming_extractor_music_svm")

PROFILE_CONF_TEMPLATE = os.path.join(BASE_DIR, "profile.conf.in")
PROFILE_CONF = os.path.join(BASE_DIR, "profile.conf")

DOCUMENTS_PER_QUERY = 100

MAX_ITEMS_PER_PROCESS = 20


class HighLevelExtractorError(Exception):
    """Indicates an error running the highlevel extractor"""


class HighLevelConfigurationError(Exception):
    """Indicates an error configuring the highlevel extractor on startup,
    before processing items"""


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]


def process_lowlevel_data(data, logger_name=None):
    """Process a set of lowlevel submissions with the highlevel binary.

    Arguments:
        data: list of up to ``MAX_ITEMS_PER_PROCESS`` (rowid, mbid, ll_data) tuples containing
         the lowlevel id of a submission, its MBID, and the actual data of the submission

    Returns:
        a list of (rowid, mbid, hl_data) tuples containing the highlevel results for the associated
         lowlevel data files. hl_data will be a dictionary

    Raises:
        ValueError: if ``data`` contains more than MAX_ITEMS_PER_PROCESS items
        ValueError: if ``data`` is empty
        HighLevelExtractorError: If lowlevel files are unable to be written to a temporary directory or
         if there is an error running the extractor binary
    """

    if len(data) > MAX_ITEMS_PER_PROCESS:
        raise ValueError("'data' cannot contain more than {} items".format(MAX_ITEMS_PER_PROCESS))
    if not data:
        raise ValueError("'data' must have some items")

    logger = None
    if logger_name:
        logger = logging.getLogger(logger_name)

    llids = ", ".join([str(llid) for llid, _, _ in data])
    if logger:
        logger.info("Starting {}".format(llids))

    try:
        working_dir = tempfile.mkdtemp(prefix="hlcalc")
    except IOError as e:
        raise HighLevelExtractorError("Unable to create temporary directory", e)

    call_args = [HIGH_LEVEL_EXTRACTOR_BINARY]
    results = []

    for rowid, mbid, ll_data in data:
        in_path = os.path.join(working_dir, '{}-input.json'.format(rowid))
        out_path = os.path.join(working_dir, '{}-output.json'.format(rowid))
        try:
            # Write this data to disk for the extractor to read. If there's an error writing a lowlevel
            # item to disk, we won't add it to the arguments. When reading the result files after execution
            # of the extractor a missing output file will raise an IOError, causing an empty result to be
            # added
            with open(in_path, 'w') as fp:
                fp.write(ll_data.encode("utf-8"))
            call_args.extend([in_path, out_path])
        except IOError:
            pass

    if not call_args:
        raise HighLevelExtractorError("Unable to write any lowlevel files to temporary directory")

    fnull = open(os.devnull, 'w')
    try:
        call_args.append(PROFILE_CONF)
        subprocess.check_call(call_args, stdout=fnull, stderr=fnull)

        for rowid, mbid, ll_data in data:
            out_file = '{}-output.json'.format(rowid)
            try:
                with open(os.path.join(working_dir, out_file), "r") as fp:
                    hl_data = json.load(fp)
            except (IOError, ValueError):
                hl_data = {}
            results.append((rowid, mbid, hl_data))

    except (subprocess.CalledProcessError, OSError):
        raise HighLevelExtractorError("Cannot call the highlevel extractor")
    finally:
        # At this point we can remove the working directory,
        # regardless of if we failed or if we succeeded
        shutil.rmtree(working_dir, ignore_errors=True)

    if logger:
        logger.info("Finished {}".format(llids))
    return results


def create_profile(in_file, out_file, sha1):
    """Prepare a profile file for use with essentia. Sanity check to make sure
    important values are present.
    """

    try:
        with open(in_file, 'r') as f:
            doc = yaml.load(f, Loader=yaml.SafeLoader)
    except IOError as e:
        raise HighLevelConfigurationError(u"Cannot read profile {}: {}".format(in_file, e))

    try:
        models_ver = doc['mergeValues']['metadata']['version']['highlevel']['models_essentia_git_sha']
    except KeyError:
        models_ver = None

    if not models_ver:
        raise HighLevelConfigurationError("{} needs to have mergeValues.metadata.version.highlevel."
                                          "models_essentia_git_sha defined".format(in_file))

    doc['mergeValues']['metadata']['version']['highlevel']['essentia_build_sha'] = sha1

    try:
        with open(out_file, 'w') as yaml_file:
            yaml.dump(doc, yaml_file, default_flow_style=False)
    except IOError as e:
        raise HighLevelConfigurationError(u"Cannot write profile {}: {}".format(out_file, e))


def get_build_sha1(binary):
    """Calculate the SHA1 of the binary we're using."""
    try:
        with open(binary, "rb") as fp:
            contents = fp.read()
    except IOError as e:
        raise HighLevelConfigurationError("Cannot calculate the SHA1 of the high-level extractor binary: {}".format(e))

    return hashlib.sha1(contents).hexdigest()


def save_hl_documents(hl_data_list, build_sha1):
    """Save a list of highlevel documents to the database.

    Arguments:
        hl_data_list: a tuple of (ll-rowid, mbid, hl_data_json)
        build_sha1: the sha1 of the hl extractor used"""

    for rowid, mbid, hl_data in hl_data_list:
        db.data.write_high_level(mbid, rowid, hl_data, build_sha1)


def main(num_threads=DEFAULT_NUM_THREADS):
    current_app.logger.info("High-level extractor daemon starting with {} threads".format(num_threads))
    if num_threads * MAX_ITEMS_PER_PROCESS > DOCUMENTS_PER_QUERY:
        current_app.logger.warn("Number of threads ({}) * items per thread ({}) = {} is greater than number of "
                                "documents selected from database ({}), this means that available resources "
                                "will not be fully utillised".format(
            num_threads, MAX_ITEMS_PER_PROCESS, (num_threads * MAX_ITEMS_PER_PROCESS), DOCUMENTS_PER_QUERY
        ))

    try:
        build_sha1 = get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY)
        create_profile(PROFILE_CONF_TEMPLATE, PROFILE_CONF, build_sha1)
    except HighLevelConfigurationError as e:
        current_app.logger.error(u'{}'.format(e))
        sys.exit(-1)

    num_processed = 0
    max_ll_id = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        while True:
            docs = db.data.get_unprocessed_highlevel_documents(DOCUMENTS_PER_QUERY, max_ll_id)
            current_app.logger.info("Got {} documents".format(len(docs)))

            futures = []
            for subdocs in chunks(docs, MAX_ITEMS_PER_PROCESS):
                futures.append(executor.submit(process_lowlevel_data, subdocs, current_app.logger.name))

            for future in concurrent.futures.as_completed(futures):
                try:
                    hl_data_list = future.result()
                except HighLevelExtractorError as e:
                    current_app.logger.error(u"Error when calling extractor: {}".format(e))
                except Exception as e:
                    traceback.print_exc()
                    current_app.logger.error(u"Unknown error when calling extractor: {}".format(e))
                else:
                    num_processed += len(hl_data_list)
                    this_max_ll_id = max([rowid for rowid, _, _ in hl_data_list])
                    max_ll_id = max(max_ll_id, this_max_ll_id)
                    save_hl_documents(hl_data_list, build_sha1)

            # If we got less than the number of documents we asked for then we should wait
            # for a while for some more to appear
            if len(docs) < DOCUMENTS_PER_QUERY:
                if num_processed > 0:
                    current_app.logger.info("processed {} documents, none remain. Sleeping.".format(num_processed))
                num_processed = 0
                time.sleep(SLEEP_DURATION)
