import logging
import time
import db.data
import db.import_mb_data

SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    logging.info("musicbrainz importer started")
    while True:
        gids_in_AB = db.data.get_new_recordings_from_lowlevel()
        if gids_in_AB:
            logging.info("Importing MusicBrainz data...")
            logging.info('Inserting data for %d recordings...' % (len(gids_in_AB)))
            db.import_mb_data.fetch_and_insert_musicbrainz_data(gids_in_AB)
        else:
            logging.info("No new recording found. Sleeping %s seconds." % SLEEP_DURATION)
            time.sleep(SLEEP_DURATION)
