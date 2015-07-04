from __future__ import print_function

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

import db
import db.data
import db.dataset
import db.dataset_eval
import db.exceptions
from db.utils import create_path
from gaia2.scripts.classification import train_model as gaia_train_model
from time import sleep
import tempfile
import shutil
import json
import yaml
import copy

import config

SLEEP_DURATION = 30  # number of seconds to wait between runs

BASE_PROJECT_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "base_project.yaml")
with open(BASE_PROJECT_FILE) as f:
    BASE_PROJECT_DICT = yaml.load(f)
BASE_GROUNDTRUTH_DICT = {
    "type": "singleClass",  # FIXME: What's that?
    "version": 1.0,         # FIXME: Is this important? Documentation?
    "className": "",        # FIXME: ???
    "groundTruth": {},
}


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
        project_dict = copy.deepcopy(BASE_PROJECT_DICT)
        project_dict["className"] = "class"  # FIXME(roman): Do we need to change this?
        project_dict["datasetsDirectory"] = os.path.join(temp_dir, "datasets")
        project_dict["resultsDirectory"] = os.path.join(temp_dir, "results")
        project_dict["filelist"] = os.path.join(temp_dir, "filelist.yaml")
        project_dict["groundtruth"] = os.path.join(temp_dir, "groundtruth.yaml")

        project_file_path = os.path.join(temp_dir, "project.yaml")
        with open(project_file_path, "w") as f:
            yaml.dump(project_dict, f)

        dataset = db.dataset.get(eval_job["dataset_id"])

        data_path = os.path.join(temp_dir, "data")
        create_path(data_path)
        filelist = dump_lowlevel_data(extract_recordings(dataset), data_path)

        with open(project_dict["filelist"], "w") as f:
            yaml.dump(filelist, f)

        with open(project_dict["groundtruth"], "w") as f:
            yaml.dump(create_groundtruth(dataset), f)

        results_model_file = os.path.join(temp_dir, "result.history")

        gaia_train_model.trainModel(
            groundtruth_file=project_dict["groundtruth"],
            filelist_file=project_dict["filelist"],
            project_file=project_file_path,
            project_dir=temp_dir,
            results_model_file=results_model_file,
        )

        # TODO: Save results in the database.

        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_DONE)

    except db.exceptions.DatabaseException:
        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_FAILED)
        # TODO(roman): Maybe log this exception? (Would also be nice to provide
        # a nice error message to the user.)

    finally:
        shutil.rmtree(temp_dir)  # Cleanup


def create_groundtruth(dataset):
    groundtruth = copy.deepcopy(BASE_GROUNDTRUTH_DICT)
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            # TODO: Implement this.
            pass
    return groundtruth


def dump_lowlevel_data(recordings, location):
    """Dumps low-level data for all recordings into specified location.

    Args:
        recordings: List of MBIDs of recordings.
        location: Path to directory where low-level data will be saved.

    Returns:
        Filelist.
    """
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
