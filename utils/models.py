import os
import os.path
import sys
import utils.path

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

HISTORY_STORAGE_DIR = os.path.join(config.FILE_STORAGE_DIR, "history")


def get_model_dir_path(job_id, create=False):
    directory = os.path.join(HISTORY_STORAGE_DIR, job_id[0:1], job_id[0:2])
    if create:
        utils.path.create_path(directory)
    return directory


def get_model_file_path(job_id, create_dir=False):
    return os.path.join(get_model_dir_path(job_id, create=create_dir), "%s.history" % job_id)
