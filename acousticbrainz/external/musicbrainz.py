import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError


def get_recording_by_id(mbid):
    # TODO: Implement caching.
    try:
        return musicbrainzngs.get_recording_by_id(mbid, includes=['artists', 'releases', 'media'])['recording']
    except ResponseError as e:
        raise DataUnavailable(e)


class DataUnavailable(Exception):
    pass
