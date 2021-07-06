import logging

ACOUSTICBRAINZ_SKLEARN_LOGGER = "acousticbrainz.models"
_logger = logging.getLogger(ACOUSTICBRAINZ_SKLEARN_LOGGER)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
_logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
