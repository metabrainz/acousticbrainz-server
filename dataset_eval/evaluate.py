from __future__ import print_function

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from dataset_eval import gaia_wrapper
import db
import db.data
import db.dataset
import db.dataset_eval
import db.exceptions
from db.utils import create_path
import gaia2.fastyaml as yaml
from time import sleep
import tempfile
import shutil
import json

import config

SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    print("Starting dataset evaluator...")
    while True:
        db.init_db_connection(config.PG_CONNECT)
        pending_job = db.dataset_eval.get_next_pending_job()
        if pending_job:
            print("Processing job %s..." % pending_job["id"])
            evaluate_dataset(pending_job)
        else:
            print("No pending datasets. Sleeping %s seconds." % SLEEP_DURATION)
            db.close_connection()
            sleep(SLEEP_DURATION)


def evaluate_dataset(eval_job):
    db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_RUNNING)
    temp_dir = tempfile.mkdtemp()

    try:
        dataset = db.dataset.get(eval_job["dataset_id"])

        filelist_path = os.path.join(temp_dir, "filelist.yaml")
        filelist = dump_lowlevel_data(extract_recordings(dataset), os.path.join(temp_dir, "data"))
        with open(filelist_path, "w") as f:
            yaml.dump(filelist, f)

        groundtruth_path = os.path.join(temp_dir, "groundtruth.yaml")
        with open(groundtruth_path, "w") as f:
            yaml.dump(create_groundtruth(dataset), f)

        results = gaia_wrapper.train_model(
            groundtruth_file=groundtruth_path,
            filelist_file=filelist_path,
            project_dir=temp_dir,
        )
        db.dataset_eval.set_job_result(eval_job["id"], json.dumps(results))
        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_DONE)

    except db.exceptions.DatabaseException:
        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_FAILED)
        # TODO(roman): Maybe log this exception? (Would also be nice to provide
        # a nice error message to the user.)

    finally:
        shutil.rmtree(temp_dir)  # Cleanup


def create_groundtruth(dataset):
    groundtruth = {
        "type": "testing",      # FIXME: What's that?
        "version": 1.0,         # FIXME: Is this important? Documentation?
        "className": "hello",   # FIXME: ???
        "groundTruth": {},
    }
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            groundtruth["groundTruth"][recording_mbid] = cls["name"]
    return groundtruth


def dump_lowlevel_data(recordings, location):
    """Dumps low-level data for all recordings into specified location.

    Args:
        recordings: List of MBIDs of recordings.
        location: Path to directory where low-level data will be saved.

    Returns:
        Filelist.
    """
    create_path(location)
    filelist = {}
    for recording in recordings:
        filelist[recording] = os.path.join(location, "%s.yaml" % recording)
        with open(filelist[recording], "w") as f:
            f.write(lowlevel_data_to_yaml(json.loads(db.data.load_low_level(recording))))
    return filelist


def lowlevel_data_to_yaml(data):
    """Prepares dictionary with low-level data about recording for processing
    and converts it into YAML string.
    """
    # Removing descriptors, that will otherwise break gaia_fusion due to
    # incompatibility of layouts (see Gaia implementation for more details).
    if 'tags' in data['metadata']:
        del data['metadata']['tags']
    if 'sample_rate' in data['metadata']['audio_properties']:
        del data['metadata']['audio_properties']['sample_rate']

    return yaml.dump(data)


def extract_recordings(dataset):
    """Extracts set of recordings used in a dataset."""
    recordings = set()
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            recordings.add(recording_mbid)
    return recordings


if __name__ == "__main__":
    main()
