"""
This script calculates accuracy of models produced by datasets submitted for challenges.
"""
from __future__ import print_function

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

import db
import db.data
import db.dataset
import db.challenge
import db.dataset_eval
import db.exceptions
import utils.path
import utils.hl_calc
import utils.models
import subprocess
import tempfile
import logging
import json
import time
import os


HIGH_LEVEL_EXTRACTOR_BINARY = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..",
    "hl_extractor",
    "streaming_extractor_music_svm"
)
PROFILE_CONF_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "profile_template.yaml")
SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    logging.info("Starting challenge submissions evaluator...")
    while True:
        db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
        eval_task = db.challenge.get_next_eval_task()
        if eval_task:
            logging.info("Processing model from job %s with snapshot %s for challenge %s..." %
                         (eval_task["job_id"], eval_task["validation_snapshot_id"], eval_task["challenge_id"]))
            result = measure_accuracy(
                model_path=utils.models.get_model_file_path(eval_task["job_id"]),
                validation_dataset=db.dataset.get_snapshot(eval_task["validation_snapshot_id"])["data"],
            )
            db.challenge.set_submission_result(
                eval_job_id=eval_task["job_id"],
                challenge_id=eval_task["challenge_id"],
                result=result,
            )
        else:
            logging.info("No pending models. Sleeping %s seconds." % SLEEP_DURATION)
            time.sleep(SLEEP_DURATION)


def measure_accuracy(model_path, validation_dataset):
    temp_dir = tempfile.mkdtemp()
    print("Measuring accuracy for a model %s in %s..." % (model_path, temp_dir))

    profile_file = os.path.join(temp_dir, "profile.conf")
    utils.hl_calc.create_profile(
        in_file=PROFILE_CONF_TEMPLATE,
        out_file=profile_file,
        sha1=utils.hl_calc.get_build_sha1(HIGH_LEVEL_EXTRACTOR_BINARY),
        models=[model_path],
    )

    results_dir = os.path.join(temp_dir, "results")

    rec_total = count_recordings_in_dataset(validation_dataset)
    rec_current = 0
    rec_correct = 0

    for cls in validation_dataset["classes"]:
        expected_value = cls["name"].lower()
        for recording in cls["recordings"]:
            rec_current += 1
            print("Extracting data for recording %s of %s..." % (rec_current, rec_total))
            current_rec_dir = os.path.join(results_dir, recording[0:1], recording[0:2], recording)
            utils.path.create_path(current_rec_dir)
            hl_output = get_hl_output(
                recording=recording,
                profile_file=profile_file,
                working_dir=current_rec_dir,
            )
            # Name (key) of the result depends on the name of the dataset, but since we expect only
            # one we can just get the first item...
            got_value = hl_output["highlevel"][hl_output["highlevel"].keys()[0]]["value"].lower()
            print("Expected value: %s. Got value: %s." % (expected_value, got_value))
            if expected_value == got_value:
                rec_correct += 1

    print("Done! %s out of %s correct results." % (rec_correct, rec_total))
    # TODO(roman): Not sure if this is the right data to store
    return {
        "correct": rec_correct,
        "total": rec_total,
    }


def count_recordings_in_dataset(dataset):
    count = 0
    for cls in dataset["classes"]:
        count += len(cls["recordings"])
    return count


def get_hl_output(recording, profile_file, working_dir):
    ll_data_file = os.path.join(working_dir, "input.json")
    with open(ll_data_file, "w+b") as f:
        # TODO(roman): This part could probably use an improvement (not selecting a random LL document)
        f.write(json.dumps(db.data.load_low_level(recording)).encode("utf-8"))

    output_file = os.path.join(working_dir, "output.json")
    open(output_file, "a").close()  # Creating output file

    devnull = open(os.devnull, 'w')
    try:
        subprocess.check_call(
            [HIGH_LEVEL_EXTRACTOR_BINARY, ll_data_file, output_file, profile_file],
            #stdout=devnull,
            #stderr=devnull,
        )
    finally:
        devnull.close()

    with open(output_file) as f:
        result = f.read()
    return json.loads(result)

if __name__ == "__main__":
    main()
