import db
from sqlalchemy import text
from brainzutils.musicbrainz_db import mb_session
from webserver.external.mbid_redirects import get_entities_by_gids
from mbdata.models import Recording


def get_original_entity(mbids):
    with mb_session() as db:
        query = db.query(Recording)

        recordings = get_entities_by_gids(
            query=query,
            entity_type='recording',
            mbids=mbids,
        )

        recording_ids = [recording.id for recording in recordings.values()]
        recording_gids = [key for key in recordings]

        gids_with_redirected_ids = dict(zip(recording_gids, recording_ids))

    return gids_with_redirected_ids

    
def get_mbids_from_gid_redirect_tables():
    with db.engine.begin() as connection:
        query = text("""
            SELECT gid
              FROM musicbrainz.recording_gid_redirect
        """)
        result = connection.execute(query)
        mbids = result.fetchall()

        recording_mbids = []
        for mbid in mbids:
            recording_mbids.append(str(mbid[0]))

        gids_with_redirected_ids = get_original_entity(recording_mbids)
