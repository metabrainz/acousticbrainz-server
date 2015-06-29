from flask import Blueprint, render_template, redirect, url_for
from acousticbrainz.data.data import load_low_level, load_high_level, get_summary_data
from acousticbrainz.data.exceptions import NoDataFoundException
from acousticbrainz.external import musicbrainz
from werkzeug.exceptions import NotFound
from urllib import quote_plus
import json
import time

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
    return render_template(
        "data/json-display.html",
        mbid=mbid,
        data=json.dumps(json.loads(load_low_level(mbid)), indent=4, sort_keys=True),
        title="Low-level JSON for %s" % mbid,
    )


@data_bp.route("/<uuid:mbid>/high-level/view", methods=["GET"])
def view_high_level(mbid):
    return render_template(
        "data/json-display.html",
        mbid=mbid,
        data=json.dumps(json.loads(load_high_level(mbid)), indent=4, sort_keys=True),
        title="High-level JSON for %s" % mbid,
    )


@data_bp.route("/<uuid:mbid>", methods=["GET"])
def summary(mbid):
    try:
        summary_data = get_summary_data(mbid)
    except NoDataFoundException:
        summary_data = {}

    info = _get_track_info(mbid, summary_data['lowlevel']['metadata'] if summary_data else None)
    if info and summary_data:
        return render_template("data/summary-complete.html", summary=summary_data, mbid=mbid, info=info,
                               tomahawk_url=_get_tomahawk_url(info))
    elif info:
        return (render_template("data/summary-metadata.html", summary=summary_data, mbid=mbid, info=info,
                                tomahawk_url=_get_tomahawk_url(info)), 404)
    else:  # When there is no data
        raise NotFound("MusicBrainz does not have data for this track.")


def _get_tomahawk_url(metadata):
    """Generates URL for iframe with Tomahawk embedded player.

    See http://toma.hk/tools/embeds.php for more info.
    """
    if not ('artist' in metadata and 'title' in metadata):
        return None
    else:
        return "http://toma.hk/embed.php?artist={artist}&title={title}".format(
            artist=quote_plus(metadata['artist'].encode("UTF-8")),
            title=quote_plus(metadata['title'].encode("UTF-8")),
        )


def _get_track_info(mbid, metadata):
    info = {}

    # Getting good metadata from MusicBrainz
    try:
        good_metadata = musicbrainz.get_recording_by_id(mbid)
    except musicbrainz.DataUnavailable:
        good_metadata = None

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

        if 'length' in good_metadata:
            info['length'] = time.strftime("%M:%S", time.gmtime(float(good_metadata['length']) / 1000))

    elif metadata:
        info['title'] = metadata['tags']['title'][0]
        info['length'] = metadata['audio_properties']['length_formatted']
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

    return info
