from __future__ import absolute_import
from flask import Blueprint, render_template, redirect, url_for, request
from webserver.external import musicbrainz
from werkzeug.exceptions import NotFound, BadRequest
from urllib import quote_plus
import db.data
import db.exceptions
import json
import time

data_bp = Blueprint("data", __name__)


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


@data_bp.route("/<uuid:mbid>/low-level/view")
def view_low_level(mbid):
    offset = request.args.get("n")
    if offset:
        if not offset.isdigit():
            raise BadRequest("Offset must be an integer value!")
        else:
            offset = int(offset)
    else:
        offset = 0

    try:
        return render_template(
            "data/json-display.html",
            mbid=mbid,
            data=json.dumps(json.loads(db.data.load_low_level(mbid, offset)),
                            indent=4, sort_keys=True),
            title="Low-level JSON for %s" % mbid,
        )
    except db.exceptions.NoDataFoundException:
        raise NotFound


@data_bp.route("/<uuid:mbid>/high-level/view")
def view_high_level(mbid):
    offset = request.args.get("n")
    if offset:
        if not offset.isdigit():
            raise BadRequest("Offset must be an integer value!")
        else:
            offset = int(offset)
    else:
        offset = 0

    try:
        return render_template(
            "data/json-display.html",
            mbid=mbid,
            data=json.dumps(json.loads(db.data.load_high_level(mbid, offset)),
                            indent=4, sort_keys=True),
            title="High-level JSON for %s" % mbid,
        )
    except db.exceptions.NoDataFoundException:
        raise NotFound


@data_bp.route("/<uuid:mbid>")
def summary(mbid):
    offset = request.args.get("n")
    if offset:
        if not offset.isdigit():
            raise BadRequest("Offset must be an integer value!")
        else:
            offset = int(offset)
    else:
        offset = 0

    try:
        summary_data = db.data.get_summary_data(mbid, offset=offset)
    except db.exceptions.NoDataFoundException:
        summary_data = {}

    recording_info = _get_recording_info(mbid, summary_data["lowlevel"]["metadata"]
                                         if summary_data else None)
    if recording_info and summary_data:
        return render_template(
            "data/summary.html",
            metadata=recording_info,
            tomahawk_url=_get_tomahawk_url(recording_info),
            submission_count=db.data.count_lowlevel(mbid),
            offset=offset,
            data=summary_data,
        )
    elif recording_info:
        return render_template("data/summary-missing.html", metadata=recording_info,
                               tomahawk_url=_get_tomahawk_url(recording_info)), 404
    else:  # Recording doesn't exist in MusicBrainz
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


def _get_recording_info(mbid, metadata):
    info = {
        'mbid': mbid,
    }

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
