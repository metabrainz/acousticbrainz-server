"""
This file consists of the setup_logger methof that is used for logging. setup_logger()
method set up a new logger object with the related configurations.

Typical usage example:
    logger = setup_logger(logger_name, logging_file_location, level_of_logging)
"""
import logging
import os

from acousticbrainz.models.sklearn.helper_functions.utils import create_directory


def setup_logger(exports_path, name, mode, level=logging.INFO):
    """
    Function to set up as many loggers as you want. It exports the logging results to a file
    in the relevant path that is determined by the configuration file.

    Args:
        exports_path: The path (str) the logging exports will be exported.
        name: The name (str) of the logger.
        level: The level (int) of the logging. Defaults to logging.INFO.
        mode: The mode (str) translated in write, append. Valid values ("w", "a")

    Returns:
        The logger object.
    """
    logs_path = create_directory(exports_path, "logs")

    # Create a custom logger
    logger = logging.getLogger(name)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(os.path.join(logs_path, "{}.log".format(name)), mode=mode)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    #  if handlers are already present and if so, clear them before adding new handlers. This is pretty convenient
    #  when debugging and the code includes the logger initialization
    if logger.hasHandlers():
        logger.handlers.clear()

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    if level is None:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(level)

    return logger
