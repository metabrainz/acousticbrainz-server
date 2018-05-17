from brainzutils import cache
from mbdata import models
from mbdata import utils
from sqlalchemy.orm import joinedload
from webserver.external.musicbrainz_database import musicbrainz_session
import exceptions as mb_exceptions

CACHE_TIMEOUT = 86400  # 1 day


def get_recording_by_id(mbid):
    mbid = str(mbid)
    recording = cache.get(mbid)
    if not recording:
        try:
            recording = _get_recording_by_id(mbid, includes=['artists', 'releases', 'media'])['recording']
        except mb_exceptions.NoDataFoundException:
            raise mb_exceptions.NoDataFoundException("Couldn't find a recording with id: {mbid}".format(mbid=mbid))
    cache.set(mbid, recording, time=CACHE_TIMEOUT)
    return recording


def _get_recording_by_id(mbid, includes=[]):
    includes_data = {}
    with musicbrainz_session() as session:
        query = session.query(models.Recording)
        if 'artists' in includes:
            # Fetch artist with artist credits
            query = query.options(joinedload("artist_credit")).\
                options(joinedload("artist_credit.artists")).\
                options(joinedload("artist_credit.artists.artist"))
        if 'media' in includes:
            # Fetch media with tracks
            query = query.options(joinedload('mediums')).\
                    options(joinedload('mediums.tracks')).\
                    options(joinedload('mediums.format')).\
                    options(joinedload('mediums.tracks.recording'))
        recordings = get_entities_by_gids(
            query=query,
            entity_type='recording',
            mbids=mbids,
        )
        if 'media' in includes:
            for release in releases.values():
                includes_data[release.id]['media'] = release.mediums

        if 'artists' in includes:
            for release_group in release_groups.values():
                artist_credit_names = release_group.artist_credit.artists
                includes_data[release_group.id]['artist-credit-names'] = artist_credit_names
                includes_data[release_group.id]['artist-credit-phrase'] = release_group.artist_credit.name

        if 'releases' in includes:
            query = db.query(models.Release).filter(getattr(models.Release, "release_group_id").in_(release_group_ids))
            for release in query:
                includes_data[release.release_group_id].setdefault('releases', []).append(release)

        recordings = {str(mbid): to_dict_recordings(recordings[mbid], includes_data[recordings[mbid].id]) for mbid in mbids}

    return recordings


def to_dict_recordings(recording, includes=None):
    if includes is None:
        includes = {}
    data = {
        'id': recording.gid,
        'name': recording.name,
        'length': recording.length,
    }
    if 'artist-credit-phrase' in includes:
        data['artist-credit-phrase'] = includes['artist-credit-phrase']

    if 'artist-credit-names' in includes:
        data['artist-credit'] = [to_dict_artist_credit_names(artist_credit_name)
                                 for artist_credit_name in includes['artist-credit-names']]

    if 'releases' in includes:
        data['release-list'] = [to_dict_releases(release) for release in includes['releases']]
    
    if 'media' in includes:
        data['medium-list'] = [to_dict_medium(medium, includes={'tracks': medium.tracks})
                               for medium in includes['media']]
    return data


def to_dict_artist_credit_names(artist_credit_name):
    data = {
        'name': artist_credit_name.name,
        'artist': to_dict_artists(artist_credit_name.artist),
    }
    if artist_credit_name.join_phrase:
        data['join_phrase'] = artist_credit_name.join_phrase
    return data


def to_dict_artists(artist, includes=None):
    if includes is None:
        includes = {}
    data = {
        'id': artist.gid,
        'name': artist.name,
        'sort_name': artist.sort_name,
    }

    if 'type' in includes and includes['type']:
        data['type'] = includes['type'].name

    return data


def to_dict_releases(release, includes=None):
    if includes is None:
        includes = {}

    data = {
        'id': release.gid,
        'name': release.name,
    }

    if 'release-groups' in includes:
        data['release-group'] = to_dict_release_groups(includes['release-groups'])

    if 'media' in includes:
        data['medium-list'] = [to_dict_medium(medium, includes={'tracks': medium.tracks})
                               for medium in includes['media']]
    return data


def to_dict_release_groups(release_group, includes=None):
    if includes is None:
        includes = {}

    data = {
        'id': release_group.gid,
        'title': release_group.name,
    }

    if 'type' in includes and includes['type']:
        data['type'] = includes['type'].name

    if 'artist-credit-phrase' in includes:
        data['artist-credit-phrase'] = includes['artist-credit-phrase']

    if 'meta' in includes and includes['meta'].first_release_date_year:
        data['first-release-year'] = includes['meta'].first_release_date_year

    if 'artist-credit-names' in includes:
        data['artist-credit'] = [to_dict_artist_credit_names(artist_credit_name)
                                 for artist_credit_name in includes['artist-credit-names']]

    if 'releases' in includes:
        data['release-list'] = [to_dict_releases(release) for release in includes['releases']]

    if 'tags' in includes:
        data['tag-list'] = includes['tags']
    return data


def to_dict_medium(medium, includes=None):
    if includes is None:
        includes = {}
    data = {
        'name': medium.name,
        'track_count': medium.track_count,
        'position': medium.position,
    }
    if medium.format:
        data['format'] = medium.format.name

    if 'tracks' in includes and includes['tracks']:
        data['track-list'] = [to_dict_track(track) for track in includes['tracks']]
    return data


def to_dict_track(track, includes=None):
    if includes is None:
        includes = {}
    data = {
        'id': track.gid,
        'name': track.name,
        'number': track.number,
        'position': track.position,
        'length': track.length,
        'recording_id': track.recording.gid,
        'recording_title': track.recording.name,
    }
    return data
