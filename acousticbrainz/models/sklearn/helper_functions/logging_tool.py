"""
This file consists of the setup_logger methof that is used for logging. setup_logger()
method set up a new logger object with the related configurations.

Typical usage example:
    logger = setup_logger(logger_name, logging_file_location, level_of_logging)
"""
import logging
import os

from acousticbrainz.models import ACOUSTICBRAINZ_SKLEARN_LOGGER
from acousticbrainz.models.sklearn.helper_functions.utils import create_directory


def setup_logger(exports_path, file_name, mode="w", level=logging.INFO):
    """
    Function to set up as many loggers as you want. It exports the logging results to a file
    in the relevant path that is determined by the configuration file.

    Args:
        exports_path: The path (str) the logging exports will be exported.
        file_name: The name (str) of the logger.
        level: The level (int) of the logging. Defaults to logging.INFO.
        mode: The mode (str) translated in write, append. Valid values ("w", "a")

    Returns:
        The logger object.
    """
    logger = logging.getLogger(ACOUSTICBRAINZ_SKLEARN_LOGGER)
    logs_path = create_directory(exports_path, "logs")

    # Create formatters and add it to handlers
    f_handler = logging.FileHandler(os.path.join(logs_path, "{}.log".format(file_name)), mode=mode)
    f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)

    # remove existing file handlers if any
    logger.handlers = [handler for handler in logger.handlers if not isinstance(handler, logging.FileHandler)]

    # Add current file handler to the logger
    logger.addHandler(f_handler)

    if level is None:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(level)

    return logger
