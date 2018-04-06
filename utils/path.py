import errno
import os
import shutil


def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise Exception("Failed to create directory structure %s. Error: %s" %
                            (path, exception))


def remove_path(path):
    """Removes a directory structure if it exists."""
    try:
        shutil.rmtree(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise Exception("Failed to remove directory structure %s. Error: %s" %
                            (path, exception))
