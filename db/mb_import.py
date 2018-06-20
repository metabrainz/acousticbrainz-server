import db
import db.import_mb_data
import logging
from sqlalchemy import text
import time

SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    logging.info("Checking if any import is required...")
    while True:
        gids_in_AB = get_new_recordings_from_AB()
        if gids_in_AB:
            logging.info("Updating AcousticBrainz database...")
            db.import_mb_data.fetch_and_insert_musicbrainz_data(gids_in_AB)
        else:
            logging.info("No new recording found. Sleeping %s seconds." % SLEEP_DURATION)
            time.sleep(SLEEP_DURATION)


def get_new_recordings_from_AB():
    with db.engine.begin() as connection:
        query = text("""SELECT lowlevel.gid
                          FROM lowlevel
                     LEFT JOIN musicbrainz.recording
                            ON lowlevel.gid = musicbrainz.recording.gid
                         WHERE musicbrainz.recording.gid is NULL
            """)
        gids = connection.execute(query)
        gids = gids.fetchall()
        gids_in_AB = [value[0] for value in gids]
        return gids_in_AB
