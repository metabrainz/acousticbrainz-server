import db
import db.data
from sqlalchemy import text
from brainzutils import musicbrainz_db
import time
import logging


def get():
    logging.info("Querying directly from AcousticBrainz database for import MB database method...")
    start_time = time.time()
    with db.engine.begin() as connection:
        query = text("""
            SELECT *
              FROM lowlevel
        INNER JOIN musicbrainz.recording
                ON musicbrainz.recording.gid = lowlevel.gid
             LIMIT 10000
        """)
        result = connection.execute(query)
        data = result.fetchall()
    first_time_taken = time.time() - start_time
    logging.info('Data imported from AcousticBrainz database in %.2f seconds.' %  first_time_taken)

    logging.info("Separate queries from AcousticBrainz and MusicBrainz databases over the direct connection...")
    start_time = time.time()
    lowlevel_data = 0
    with db.engine.begin() as connection:
        query = text("""
            SELECT *
              FROM lowlevel
             LIMIT 10000
        """)
        result = connection.execute(query)
        lowlevel_data = result.fetchall()

    lowlevel_data = list({value['gid'] for value in lowlevel_data})
    with musicbrainz_db.engine.begin() as connection:
        query = text("""
            SELECT *
              FROM recording
             WHERE recording.gid in :gids
        """)
        result = connection.execute(query, {"gids": tuple(lowlevel_data)})
        rec_data = result.fetchall()
    second_time_taken = time.time() - start_time
    logging.info('Data imported from direct connection to MusicBrainz database in %.2f seconds.' %  second_time_taken)
