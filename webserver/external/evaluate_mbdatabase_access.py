import db
import db.data
import time
import logging
from sqlalchemy import text
from brainzutils import musicbrainz_db


def get():
    logging.info("Querying directly from AcousticBrainz database for import MB database method...")
    start_time = time.time()

    data = db.data.load_lowlevel_and_recording_data()

    first_time_taken = time.time() - start_time
    logging.info('Data imported from AcousticBrainz database in %.2f seconds.' %  first_time_taken)

    logging.info("Separate queries from AcousticBrainz and MusicBrainz databases over the direct connection...")
    start_time = time.time()

    lowlevel_data = db.data.load_lowlevel_data()
    lowlevel_data = list({value['gid'] for value in lowlevel_data})

    recording_data = db.data.load_recording_data_from_MB_db(lowlevel_data)

    second_time_taken = time.time() - start_time
    logging.info('Data imported from direct connection to MusicBrainz database in %.2f seconds.' %  second_time_taken)
