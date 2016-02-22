from __future__ import absolute_import
from flask import Blueprint, render_template, redirect, url_for, request
from webserver.external import musicbrainz
from werkzeug.exceptions import NotFound, BadRequest
from six.moves.urllib.parse import quote_plus
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
            data=json.dumps(db.data.load_low_level(mbid, offset),
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
            data=json.dumps(db.data.load_high_level(mbid, offset),
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

    if summary_data.get("highlevel"):
        genres, moods, other = _interpret_high_level(summary_data["highlevel"])
        if genres or moods or other:
            summary_data["highlevel"] = {
                "genres": genres,
                "moods": moods,
                "other": other,
            }

    recording_info = _get_recording_info(mbid, summary_data["lowlevel"]["metadata"]
                                         if summary_data else None)
    if recording_info and summary_data:
        submission_count = db.data.count_lowlevel(mbid)
        return render_template(
            "data/summary.html",
            metadata=recording_info,
            tomahawk_url=_get_tomahawk_url(recording_info),
            submission_count=submission_count,
            position=offset + 1,
            previous=offset - 1 if offset > 0 else None,
            next=offset + 1 if offset < submission_count - 1 else None,
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
        if good_metadata['release-list']:
            release = good_metadata['release-list'][0]
            info['release_id'] = release['id']
            info['release'] = release['title']
            info['track_id'] = release['medium-list'][0]['track-list'][0]['id']
            info['track_number'] = \
                '%s / %s' % (release['medium-list'][0]['track-list'][0]['number'],
                             release['medium-list'][0]['track-count'])
        if 'length' in good_metadata:
            info['length'] = time.strftime("%M:%S", time.gmtime(float(good_metadata['length']) / 1000))
        return info

    elif metadata:

        def get_tag(name):
            if name in metadata['tags'] and metadata['tags'][name]:
                return metadata['tags'][name][0]
            else:
                return ''

        info['length'] = metadata['audio_properties']['length_formatted']
        info['title'] = get_tag('title')
        info['artist_id'] = get_tag('musicbrainz_artistid')
        info['artist'] = get_tag('artist')
        info['release_id'] = get_tag('musicbrainz_albumid')
        info['release'] = get_tag('album')
        info['track_id'] = get_tag('musicbrainz_releasetrackid')
        if 'tracktotal' in metadata['tags']:
            info['track_number'] = '%s / %s' % (get_tag('tracknumber'),
                                                get_tag('tracktotal'))
        else:
            info['track_number'] = get_tag('tracknumber')
        return info

    else:
        return {}


def _interpret_high_level(hl):

    def interpret(text, data, threshold=.6):
        if data['probability'] >= threshold:
            return text, data['value'].replace("_", " "), "%.3f" % data['probability']
        else:
            return text, "unsure", "%.3f" % data['probability']

    genres = []
    tzan = hl['highlevel'].get('genre_tzanetakis')
    if tzan:
        genres.append(interpret("Tzanetakis model", tzan))
    elec = hl['highlevel'].get('genre_electronic')
    if elec:
        genres.append(interpret("Electronic classification", elec))
    dort = hl['highlevel'].get('genre_dortmund')
    if dort:
        genres.append(interpret("Dortmund model", dort))
    ros = hl['highlevel'].get('genre_rosamerica')
    if ros:
        genres.append(interpret("Rosamerica model", ros))

    moods = []
    elec = hl['highlevel'].get('mood_electronic')
    if elec:
        moods.append(interpret("Electronic", elec))
    party = hl['highlevel'].get('mood_party')
    if party:
        moods.append(interpret("Party", party))
    aggressive = hl['highlevel'].get('mood_aggressive')
    if aggressive:
        moods.append(interpret("Aggressive", aggressive))
    acoustic = hl['highlevel'].get('mood_acoustic')
    if acoustic:
        moods.append(interpret("Acoustic", acoustic))
    happy = hl['highlevel'].get('mood_happy')
    if happy:
        moods.append(interpret("Happy", happy))
    sad = hl['highlevel'].get('mood_sad')
    if sad:
        moods.append(interpret("Sad", sad))
    relaxed = hl['highlevel'].get('mood_relaxed')
    if relaxed:
        moods.append(interpret("Relaxed", relaxed))
    mirex = hl['highlevel'].get('mood_mirex')
    if mirex:
        moods.append(interpret("Mirex method", mirex))

    other = []
    voice = hl['highlevel'].get('voice_instrumental')
    if voice:
        other.append(interpret("Voice", voice))
    gender = hl['highlevel'].get('gender')
    if gender:
        other.append(interpret("Gender", gender))
    dance = hl['highlevel'].get('danceability')
    if dance:
        other.append(interpret("Danceability", dance))
    tonal = hl['highlevel'].get('tonal_atonal')
    if tonal:
        other.append(interpret("Tonal", tonal))
    timbre = hl['highlevel'].get('timbre')
    if timbre:
        other.append(interpret("Timbre", timbre))
    rhythm = hl['highlevel'].get('ismir04_rhythm')
    if rhythm:
        other.append(interpret("ISMIR04 Rhythm", rhythm))

    return genres, moods, other
