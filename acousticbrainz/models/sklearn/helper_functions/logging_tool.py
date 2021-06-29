"""
This file consists of the LoggerSetup class that is used for logging.

Here, the LoggerSetup and its embedded setup_logger() method set up a new logger object with the related configurations.

    Typical usage example:

    logging_object = LoggerSetup(logger_name, logging_file_location, level_of_logging)
    logger = logging_object.setup_logger()
"""
import logging
import os
from ..helper_functions.utils import FindCreateDirectory

# # load yaml configuration file to a dict
# config_data = load_yaml()
# # If log directory does not exist, create one
# current_d = os.getcwd()
# if config_data["log_directory"] is None or config_data["log_directory"] is None:
#     if not os.path.exists(os.path.join(current_d, "logs_dir")):
#         os.makedirs(os.path.join(current_d, "logs_dir"))
#         log_path = os.path.join(current_d, "logs_dir")
# else:
#     log_path = FindCreateDirectory(config_data["log_directory"]).inspect_directory()


class LoggerSetup:
    """It sets up a logging object.

    Attributes:
        name: The name of the logger.
        log_file: The path of the logging file export.
        level: An integer that defines the logging level.
    """
    def __init__(self, config, exports_path, name, train_class, mode, level=1):
        """
        Inits the logger object with the corresponding parameters.

        Args:
            config: The configuration data (dict).
            exports_path: The path (str) the logging exports will be exported.
            name: The name (str) of the logger.
            train_class: The name of the target class (str)
            level: The level (int) of the logging. Defaults to 1.
            mode: The mode (str) translated in write, append. Valid values ("w", "a")
        """
        self.config = config
        self.exports_path = exports_path
        self.name = name
        self.train_class = train_class
        self.mode = mode
        self.level = level

        self.exports_dir = ""
        self.logs_path = ""

    def setup_logger(self):
        """
        Function to set up as many loggers as you want. It exports the logging results to a file
        in the relevant path that is determined by the configuration file.

        Returns:
            The logger object.
        """
        self.exports_dir = self.config.get("exports_directory")
        self.logs_path = FindCreateDirectory(self.exports_path,
                                             os.path.join(self.exports_dir, "logs")).inspect_directory()

        # Create a custom logger
        logger_object = logging.getLogger(self.name)

        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(os.path.join(self.logs_path, "{}.log".format(self.name)), mode=self.mode)

        # Create formatters and add it to handlers
        c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        #  if handlers are already present and if so, clear them before adding new handlers. This is pretty convenient
        #  when debugging and the code includes the logger initialization
        if logger_object.hasHandlers():
            logger_object.handlers.clear()

        # Add handlers to the logger
        logger_object.addHandler(c_handler)
        logger_object.addHandler(f_handler)

        if self.level is None:
            logger_object.setLevel(logging.INFO)
        elif self.level == "logging.DEBUG":
            logger_object.setLevel(logging.DEBUG)
        elif self.level == "logging.INFO":
            logger_object.setLevel(logging.INFO)
        elif self.level == "logging.WARNING":
            logger_object.setLevel(logging.WARNING)
        elif self.level == "logging.ERROR":
            logger_object.setLevel(logging.ERROR)
        elif self.level == "logging.CRITICAL":
            logger_object.setLevel(logging.CRITICAL)
        else:
            print("Please define correct one of the Debug Levels:\n"
                  "logging.DEBUG: DEBUG\n"
                  "logging.INFO: INFO\n"
                  "logging.WARNING: WARNING\n"
                  "logging.ERROR: ERROR\n"
                  "logging.CRITICAL: CRITICAL")

        return logger_object
