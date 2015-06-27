from web_server.utils import sanity_check_data, clean_metadata, interpret_high_level
from web_server.data import create_cursor, commit
from web_server.data.exceptions import NoDataFoundException
from werkzeug.exceptions import BadRequest, NotFound
from flask import current_app
from hashlib import sha256
import json
import time


def submit_low_level_data(mbid, data):
    """Function for submitting low-level data.

    Args:
        mbid: MusicBrainz ID of the track that corresponds to the data that is
            being submitted.
        data: Low-level data about the track.
    """
    mbid = str(mbid)
    data = clean_metadata(data)

    try:
        # If the user submitted a trackid key, rewrite to recording_id
        if "musicbrainz_trackid" in data['metadata']['tags']:
            val = data['metadata']['tags']["musicbrainz_trackid"]
            del data['metadata']['tags']["musicbrainz_trackid"]
            data['metadata']['tags']["musicbrainz_recordingid"] = val

        if data['metadata']['audio_properties']['lossless']:
            data['metadata']['audio_properties']['lossless'] = True
        else:
            data['metadata']['audio_properties']['lossless'] = False

    except KeyError:
        pass

    missing_key = sanity_check_data(data)
    if missing_key is not None:
        raise BadRequest("Key '%s' was not found in submitted data." % ' : '.join(missing_key))

    # Ensure the MBID form the URL matches the recording_id from the POST data
    if data['metadata']['tags']["musicbrainz_recordingid"][0].lower() != mbid.lower():
        raise BadRequest("The musicbrainz_trackid/musicbrainz_recordingid in"
                         "the submitted data does not match the MBID that is"
                         "part of this resource URL.")

    # The data looks good, lets see about saving it
    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    build_sha1 = data['metadata']['version']['essentia_build_sha']
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json).hexdigest()

    with create_cursor() as cursor:
        # Checking to see if we already have this data
        cursor.execute("SELECT data_sha256 FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have this data already, add it
        sha_values = [v[0] for v in cursor.fetchall()]

        if data_sha256 not in sha_values:
            current_app.logger.info("Saved %s" % mbid)
            cursor.execute(
                "INSERT INTO lowlevel (mbid, build_sha1, data_sha256, lossless, data)"
                "VALUES (%s, %s, %s, %s, %s)",
                (mbid, build_sha1, data_sha256, is_lossless_submit, data_json)
            )
            commit()
            return ""

        current_app.logger.info("Already have %s" % data_sha256)


def load_low_level(mbid, offset=0):
    """Load low-level data for a given MBID."""
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT data::text FROM lowlevel WHERE mbid = %s OFFSET %s",
            (str(mbid), offset)
        )
        if not cursor.rowcount:
            raise NotFound

        row = cursor.fetchone()
        return row[0]


def load_high_level(mbid):
    """Load high-level data for a given MBID."""
    with create_cursor() as cursor:
        cursor.execute("""SELECT hlj.data::text
                            FROM highlevel hl
                            JOIN highlevel_json hlj
                              ON hl.data = hlj.id
                           WHERE mbid = %s""", (str(mbid), ))
        if not cursor.rowcount:
            raise NotFound

        row = cursor.fetchone()
        return row[0]


def count_lowlevel(mbid):
    """Count number of stored low-level submissions for a specified MBID."""
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM lowlevel WHERE mbid = %s",
            (str(mbid),)
        )
        return cursor.fetchone()[0]


def get_summary_data(mbid):
    """Fetches the low-level and high-level features from for the specified MBID."""
    summary = {}
    mbid = str(mbid)
    with create_cursor() as cursor:
        cursor.execute("SELECT data FROM lowlevel WHERE mbid = %s", (mbid, ))
        if not cursor.rowcount:
            raise NoDataFoundException("Can't find low-level data for this recording.")

        row = cursor.fetchone()
        lowlevel = row[0]
        if 'artist' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['artist'] = ["[unknown]"]
        if 'release' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['release'] = ["[unknown]"]
        if 'title' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['title'] = ["[unknown]"]

        lowlevel['metadata']['audio_properties']['length_formatted'] = \
            time.strftime("%M:%S", time.gmtime(lowlevel['metadata']['audio_properties']['length']))

        summary['lowlevel'] = lowlevel

        cursor.execute(
            "SELECT hlj.data "
            "FROM highlevel hl, highlevel_json hlj "
            "WHERE hl.data = hlj.id "
            "AND hl.mbid = %s",
            (mbid, )
        )
        if cursor.rowcount:
            summary['highlevel'] = cursor.fetchone()[0]
            try:
                summary['genres'], summary['moods'], summary['other'] = \
                    interpret_high_level(summary['highlevel'])
            except KeyError:
                pass

        return summary
