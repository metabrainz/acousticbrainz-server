import db
import db.data
from sqlalchemy import text
from brainzutils.musicbrainz_db import mb_session
from brainzutils.musicbrainz_db.utils import get_entities_by_gids
from mbdata.models import Recording


def get_original_entity():
    """Get original entity information after applying MBID redirect
    to many mbids.

    Args:
        mbids (list): list of uuid (MBID(gid)) of the recordings.
    Returns:
        Dictionary containing the redirected original entity ids with MBIDs as keys.
            - mbid: Recording mbids of the entities
            - id: Original redirected ids of the entities after mbid redirect
    """
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
