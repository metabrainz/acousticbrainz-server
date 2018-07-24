import logging
import time
import db.data
import db.import_mb_data
from flask import current_app

SLEEP_DURATION = 30  # number of seconds to wait between runs
BATCH_SLEEP_DURATION = 5 # number of seconds to wait between batches


def main():
    logging.info("musicbrainz importer started")
    while True:
        gids_in_AB = db.data.get_new_recordings_from_lowlevel()
        if gids_in_AB:
            logging.info("Importing MusicBrainz data...")
            logging.info('Inserting data for %d recordings...' % (len(gids_in_AB)))
            db.import_mb_data.fetch_and_insert_musicbrainz_data(gids_in_AB)
            batch_sleep = current_app.config['BATCH_SLEEP_DURATION']
            logging.info("Sleeping %s seconds before starting next batch's import." % batch_sleep)
            time.sleep(batch_sleep)
        else:
            sleep = current_app.config['SLEEP_DURATION']
            logging.info("No new recording found. Sleeping %s seconds." % sleep)
            time.sleep(sleep)
