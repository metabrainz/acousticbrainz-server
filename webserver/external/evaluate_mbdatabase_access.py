import db
import db.data
from sqlalchemy import text
from brainzutils import musicbrainz_db
import time
import logging


def get():
    s_t = time.time()
    print "Query directly from AcousticBrainz database for Import db method"
    with db.engine.begin() as connection:
        query = text("""
            SELECT *
              FROM lowlevel
        INNER JOIN musicbrainz.recording
                ON musicbrainz.recording.gid = lowlevel.gid"""
        )
        result = connection.execute(query)
        data = result.fetchall()
    print time.time()-s_t

    print "Separate queries from AcousticBrainz and MusicBrainz database over the direct connection"
    n_t = time.time()
    lowlevel_data = 0
    with db.engine.begin() as connection:
        query = text("""
            SELECT *
              FROM lowlevel
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
    print time.time() - n_t
