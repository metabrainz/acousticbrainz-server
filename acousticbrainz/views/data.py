from flask import Blueprint, render_template, redirect, url_for
from acousticbrainz.data import load_low_level, load_high_level, get_summary_data
from acousticbrainz.external import musicbrainz
from urllib import quote_plus
import json

data_bp = Blueprint('data', __name__)


@data_bp.route("/api")
def api():
    return redirect(url_for(".data"))


@data_bp.route("/data")
def data():
    return render_template("data/data.html")


@data_bp.route("/recording/<uuid:mbid>")
def recording(mbid):
    """Endpoint for MusicBrainz style recording URLs (https://musicbrainz.org/recording/<mbid>).

    Basic wrapper for `summary` endpoint that makes it easier to move from
    MusicBrainz to AcousticBrainz.
    """
    return redirect(url_for(".summary", mbid=mbid))


@data_bp.route("/<uuid:mbid>/low-level/view", methods=["GET"])
def view_low_level(mbid):
    data = json.dumps(json.loads(load_low_level(mbid)), indent=4, sort_keys=True)
    return render_template("data/json-display.html", mbid=mbid, data=data,
                           title="Low-level JSON for %s" % mbid)


@data_bp.route("/<uuid:mbid>/high-level/view", methods=["GET"])
def view_high_level(mbid):
    data = json.dumps(json.loads(load_high_level(mbid)), indent=4, sort_keys=True)
    return render_template("data/json-display.html", mbid=mbid, data=data,
                           title="High-level JSON for %s" % mbid)


@data_bp.route("/<uuid:mbid>", methods=["GET"])
def summary(mbid):
    lowlevel, highlevel, genres, moods, other = get_summary_data(mbid)

    info = _get_track_info(mbid, lowlevel['metadata'])

    # Tomahawk player stuff
    if not ('artist' in lowlevel['metadata']['tags'] and 'title' in lowlevel['metadata']['tags']):
        tomahawk_url = None
    else:
        tomahawk_url = "http://toma.hk/embed.php?artist={artist}&title={title}".format(
            artist=quote_plus(info['artist'].encode("UTF-8")),
            title=quote_plus(info['title'].encode("UTF-8")))

    return render_template("data/summary.html", lowlevel=lowlevel, highlevel=highlevel,
                           genres=genres, moods=moods, other=other, mbid=mbid,
                           info=info, tomahawk_url=tomahawk_url)


def _get_track_info(mbid, metadata):
    info = {}

    # Getting good metadata from MusicBrainz
    good_metadata = musicbrainz.get_recording_by_id(mbid)

    if good_metadata:
        info['title'] = good_metadata['title']
        info['artist_id'] = good_metadata['artist-credit'][0]['artist']['id']
        info['artist'] = good_metadata['artist-credit-phrase']
        info['release_id'] = good_metadata['release-list'][0]['id']
        info['release'] = good_metadata['release-list'][0]['title']
        info['track_id'] = good_metadata['release-list'][0]['medium-list'][0]['track-list'][0]['id']
        info['track_number'] = \
            '%s / %s' % (good_metadata['release-list'][0]['medium-list'][0]['track-list'][0]['number'],
                         good_metadata['release-list'][0]['medium-list'][0]['track-count'])

    else:
        info['title'] = metadata['tags']['title'][0]
        info['artist_id'] = metadata['tags']['musicbrainz_artistid'][0]
        info['artist'] = metadata['tags']['artist'][0]
        info['release_id'] = metadata['tags']['musicbrainz_albumid'][0]
        info['release'] = metadata['tags']['album'][0]
        info['track_id'] = metadata['tags']['musicbrainz_releasetrackid'][0] if \
            'musicbrainz_releasetrackid' in metadata['tags'] else None

        if 'tracktotal' in metadata['tags']:
            info['track_number'] = '%s / %s' % (metadata['tags']['tracknumber'][0],
                                                metadata['tags']['tracktotal'][0])
        else:
            info['track_number'] = metadata['tags']['tracknumber'][0]

    info['length'] = metadata['audio_properties']['length_formatted']

    return info
