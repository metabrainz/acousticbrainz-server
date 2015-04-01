from flask import Blueprint, render_template, redirect, url_for
from acousticbrainz.data import load_low_level, load_high_level, get_summary_data
from musicbrainzngs.musicbrainz import ResponseError
from urllib import quote_plus
import musicbrainzngs
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

    info = None

    if lowlevel == None: # No metadata in acousticbrainz.. try to fetch data from musicbrainz
        info = _get_track_info(mbid)
    else: # Try to get metadata from musicbrainz with second priority as the one retrieved from acoustic
        info = _get_track_info(mbid, lowlevel['metadata'])


    # Tomahawk player stuff
    # Put additional check if the lowlevel has the metadata ????
    # Why not directly take the data from info if present (doing that)
    # Not checking if info is None or not because it is nver None

    if not ('artist' in info and 'title' in info):
        tomahawk_url = None
    else:
        tomahawk_url = "http://toma.hk/embed.php?artist={artist}&title={title}".format(
            artist=quote_plus(info['artist'].encode("UTF-8")),
            title=quote_plus(info['title'].encode("UTF-8")))

    # Checking for what all information we have and rendering the pages accordingly..

    if lowlevel and info: # When we have the data from the acousticbrainz available.. the happy condition..
        return render_template("data/summary.html", lowlevel=lowlevel, highlevel=highlevel,
                                genres=genres, moods=moods, other=other, mbid=mbid,
                                info=info, tomahawk_url=tomahawk_url)
    
    elif info: # When there is only metadata... TODO: Move into the same template with if conditions...
        return render_template("data/summary-metadata.html", info = info, tomahawk_url = tomahawk_url, mbid=mbid)
    
    else: # When there is no data
        raise NotFound("MusicBrainz does not have data for this track. Please upload it!")


def _get_track_info(mbid, metadata = None): # Defaulting the metadata to None
    info = {}

    # Getting good metadata from MusicBrainz
    try:
        good_metadata = musicbrainzngs.get_recording_by_id(
            mbid, includes=['artists', 'releases', 'media'])['recording']
    except ResponseError:
        good_metadata = None

    if good_metadata:
        info['title'] = good_metadata['title']
        if 'length' in good_metadata:
            info['length'] = float(good_metadata['length']) / 1000 # Concerting from ms to s
        info['artist_id'] = good_metadata['artist-credit'][0]['artist']['id']
        info['artist'] = good_metadata['artist-credit-phrase']
        info['release_id'] = good_metadata['release-list'][0]['id']
        info['release'] = good_metadata['release-list'][0]['title']
        info['track_id'] = good_metadata['release-list'][0]['medium-list'][0]['track-list'][0]['id']
        info['track_number'] = \
            '%s / %s' % (good_metadata['release-list'][0]['medium-list'][0]['track-list'][0]['number'],
                         good_metadata['release-list'][0]['medium-list'][0]['track-count'])

    elif metadata != None: # Check if the metadata is not 'None'
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

    # Giving priority to the data fetched from musicbrainz..
    if 'length' in info:
        info['length'] = time.strftime("%M:%S", time.gmtime(info['length']))
    # If not in musicbrainz, try to get from AB data.
    elif metadata and 'audio_properties' in metadata:        
        info['length'] = metadata['audio_properties']['length_formatted']
    return info
