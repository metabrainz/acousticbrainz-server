import db
from flask import current_app
from sqlalchemy import text

def get_new_recordings_from_lowlevel():
    with db.engine.begin() as connection:
        rows_to_fetch = current_app.config['RECORDINGS_FETCHED_PER_BATCH']

        query = text("""SELECT lowlevel.gid
                          FROM lowlevel
                     LEFT JOIN musicbrainz.recording
                            ON lowlevel.gid = musicbrainz.recording.gid
                         WHERE musicbrainz.recording.gid is NULL
                      ORDER BY lowlevel.id
                         LIMIT :rows_to_fetch
        """)
        gids = connection.execute(query, {"rows_to_fetch": rows_to_fetch})
        gids = gids.fetchall()
        gids_in_AB = [value[0] for value in gids]

        return gids_in_AB
