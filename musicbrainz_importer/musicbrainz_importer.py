import db
import db.import_mb_data
import logging
from sqlalchemy import text
import time
from flask import current_app

SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    logging.info("musicbrainz importer started")
    while True:
        gids_in_AB, rows_to_fetch = get_new_recordings_from_AB()
        if gids_in_AB:
            logging.info("Importing MusicBrainz data...")
            logging.info('Inserting data for %d recordings...' % (rows_to_fetch))
            db.import_mb_data.fetch_and_insert_musicbrainz_data(gids_in_AB)
        else:
            logging.info("No new recording found. Sleeping %s seconds." % SLEEP_DURATION)
            time.sleep(SLEEP_DURATION)


def get_new_recordings_from_AB():
    with db.engine.begin() as connection:
        offset = 0
        rows_to_fetch = current_app.config['RECORDINGS_FETCHED_PER_BATCH']

        query = text("""SELECT lowlevel.gid
                          FROM lowlevel
                     LEFT JOIN musicbrainz.recording
                            ON lowlevel.gid = musicbrainz.recording.gid
                         WHERE musicbrainz.recording.gid is NULL
                      ORDER BY lowlevel.id
                        OFFSET :offset
                         LIMIT :rows_to_fetch
        """)
        gids = connection.execute(query, {"offset": offset, "rows_to_fetch": rows_to_fetch})
        gids = gids.fetchall()
        gids_in_AB = [value[0] for value in gids]
        offset = offset + rows_to_fetch

        return gids_in_AB, rows_to_fetch
