import db
import db.data
import time
import logging
from sqlalchemy import text
from brainzutils.musicbrainz_db import mb_session
from brainzutils.musicbrainz_db.utils import get_entities_by_gids
from mbdata.models import Recording


def get_original_entity(database):
    """Get original entity information after applying MBID redirect
    to many mbids.

    Args:
        mbids (list): list of uuid (MBID(gid)) of the recordings.
    Returns:
        Dictionary containing the redirected original entity ids with MBIDs as keys.
            - mbid: Recording mbids of the entities
            - id: Original redirected ids of the entities after mbid redirect
    """
    if database == 'MB':
        mbids = db.data.get_mbids_from_gid_redirect_tables_from_MB_db()
    else:
        mbids = db.data.get_mbids_from_gid_redirect_tables()
    with mb_session() as mb_db:
        query = mb_db.query(Recording)

        recordings = get_entities_by_gids(
            query=query,
            entity_type='recording',
            mbids=mbids,
        )

        recording_ids = [recording.id for recording in recordings.values()]
        recording_gids = [key for key in recordings]

        gids_with_redirected_ids = dict(zip(recording_gids, recording_ids))

        return gids_with_redirected_ids


def main():
    # Testing with the MusicBrainz schema in AB
    start_time = time.time()

    gids_with_redirected_ids = get_original_entity('AB')

    first_time_taken = time.time() - start_time
    logging.info('Data imported from AcousticBrainz database in %.2f seconds.' %  first_time_taken)

    # Testing with the original MusicBrainz database over the direct connection
    start_time = time.time()

    gids_with_redirected_ids = get_original_entity('AB')

    second_time_taken = time.time() - start_time
    logging.info('Data imported from direct connection to MusicBrainz database in %.2f seconds.' %  second_time_taken)
