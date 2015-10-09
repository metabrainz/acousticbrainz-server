from hashlib import sha256
import logging
import copy
import time
import json
import os
import db
import db.exceptions


_whitelist_file = os.path.join(os.path.dirname(__file__), "tagwhitelist.json")
_whitelist_tags = set(json.load(open(_whitelist_file)))

SANITY_CHECK_KEYS = [
    ['metadata', 'version', 'essentia'],
    ['metadata', 'version', 'essentia_git_sha'],
    ['metadata', 'version', 'extractor'],
    ['metadata', 'version', 'essentia_build_sha'],
    ['metadata', 'audio_properties', 'length'],
    ['metadata', 'audio_properties', 'bit_rate'],
    ['metadata', 'audio_properties', 'codec'],
    ['metadata', 'audio_properties', 'lossless'],
    ['metadata', 'tags', 'file_name'],
    ['metadata', 'tags', 'musicbrainz_recordingid'],
    ['lowlevel'],
    ['rhythm'],
    ['tonal'],
]

# TODO: Util methods should not be in the database package

def _has_key(dictionary, key):
    """Checks if muti-level dictionary contains in item referenced by a
    specified key.

    Args:
        dictionary: Multi-level dictionary that needs to be checked.
        keys: List of keys that will be checked. For example, key
            ['metadata', 'tags'] represents dictionary['metadata']['tags'].
    Returns:
        True if dictionary contains item with a specified key, False if it
        wasn't found.
    """
    for part in key:
        if part not in dictionary:
            return False
        dictionary = dictionary[part]
    return True


def sanity_check_data(data):
    """Checks if data about the recording contains all required keys.

    Args:
        data: Dictionary that contains information about the recording.
    Returns:
        First key that is missing or None if everything is in place.
    """
    for key in SANITY_CHECK_KEYS:
        if not _has_key(data, key):
            return key
    return None


def clean_metadata(data):
    """Check that tags are in our whitelist. If not, throw them away."""
    cleaned_tags = copy.deepcopy(data["metadata"]["tags"])
    for tag in data["metadata"]["tags"].keys():
        if tag.lower() not in _whitelist_tags:
            del cleaned_tags[tag]
    data["metadata"]["tags"] = cleaned_tags
    return data


def submit_low_level_data(mbid, data):
    """Function for submitting low-level data.

    Args:
        mbid: MusicBrainz ID of the recording that corresponds to the data
            that is being submitted.
        data: Low-level data about the recording.
    """
    mbid = str(mbid)
    data = clean_metadata(data)

    try:
        # If the user submitted a trackid key, rewrite to recording_id
        if 'musicbrainz_trackid' in data['metadata']['tags']:
            val = data['metadata']['tags']['musicbrainz_trackid']
            del data['metadata']['tags']['musicbrainz_trackid']
            data['metadata']['tags']['musicbrainz_recordingid'] = val

        if data['metadata']['audio_properties']['lossless']:
            data['metadata']['audio_properties']['lossless'] = True
        else:
            data['metadata']['audio_properties']['lossless'] = False

    except KeyError:
        pass

    missing_key = sanity_check_data(data)
    if missing_key is not None:
        raise db.exceptions.BadDataException(
            "Key '%s' was not found in submitted data." %
            ' : '.join(missing_key)
        )

    # Ensure the MBID form the URL matches the recording_id from the POST data
    if data['metadata']['tags']['musicbrainz_recordingid'][0].lower() != mbid.lower():
        raise db.exceptions.BadDataException(
            "The musicbrainz_trackid/musicbrainz_recordingid in "
            "the submitted data does not match the MBID that is "
            "part of this resource URL."
        )

    # The data looks good, lets see about saving it
    write_low_level(mbid, data)


def write_low_level(mbid, data):

    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    build_sha1 = data['metadata']['version']['essentia_build_sha']
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()
    with db.engine.connect() as connection:
        # Checking to see if we already have this data
        result = connection.execute("SELECT data_sha256 FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have this data already, add it
        sha_values = [v[0] for v in result.fetchall()]

        if data_sha256 not in sha_values:
            logging.info("Saved %s" % mbid)
            connection.execute(
                "INSERT INTO lowlevel (mbid, build_sha1, data_sha256, lossless, data)"
                "VALUES (%s, %s, %s, %s, %s)",
                (mbid, build_sha1, data_sha256, is_lossless_submit, data_json)
            )
        else:
            logging.info("Already have %s" % data_sha256)

def write_high_level(mbid, ll_id, data, build_sha1):
    norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    sha = sha256(norm_data).hexdigest()

    with db.engine.connect() as connection:
        result = connection.execute("""INSERT INTO highlevel_json (data, data_sha256)
                                            VALUES (%s, %s)
                                         RETURNING id""", (norm_data, sha))
        id = result.fetchone()[0]
        connection.execute("""INSERT INTO highlevel (id, mbid, build_sha1, data, submitted)
                                   VALUES (%s, %s, %s, %s, now())""",
                           (ll_id, mbid, build_sha1, id))


def load_low_level(mbid, offset=0):
    """Load lowlevel data with the given mbid as a dictionary.
    If no offset is given, return the first. If an offset is
    given (from 0), return the relevent item.

    Raises db.exceptions.NoDataFoundException if the mbid doesn't
    exist or if the offset is too high."""
    with db.engine.connect() as connection:
        result = connection.execute(
            """SELECT data
                 FROM lowlevel
                WHERE mbid = %s
             ORDER BY submitted
               OFFSET %s""",
            (str(mbid), offset)
        )
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException

        row = result.fetchone()
        return row[0]


def load_high_level(mbid, offset=0):
    """Load high-level data for a given MBID."""
    with db.engine.connect() as connection:
        result = connection.execute(
            """SELECT hlj.data
                 FROM highlevel hl
                 JOIN highlevel_json hlj
                   ON hl.data = hlj.id
                 JOIN lowlevel ll
                   ON ll.id = hl.id
                WHERE ll.mbid = %s
             ORDER BY ll.submitted
               OFFSET %s""",
            (str(mbid), offset)
        )
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException
        return result.fetchone()[0]


def count_lowlevel(mbid):
    """Count number of stored low-level submissions for a specified MBID."""
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT count(*) FROM lowlevel WHERE mbid = %s",
            (str(mbid),)
        )
        return result.fetchone()[0]

def get_unprocessed_highlevel_documents():
    """Fetch up to 100 low-level documents which have no associated high level data."""
    with db.engine.connect() as connection:
        result = connection.execute("""SELECT ll.mbid, ll.data::text, ll.id
                         FROM lowlevel AS ll
                    LEFT JOIN highlevel AS hl
                           ON ll.id = hl.id
                        WHERE hl.mbid IS NULL
                        LIMIT 100""")
        docs = result.fetchall()
        return docs


def get_summary_data(mbid, offset=0):
    """Fetches the low-level and high-level features from for the specified MBID.

    Args:
        offset: Offset can be specified if you need to get summary for a
        different submission. They are ordered by creation time.

    Returns:
        Dictionary with low-level data ("lowlevel" key) for the specified MBID
        and, if it has been calculated, high-level data ("highlevel" key).
    """
    summary = {}
    mbid = str(mbid)
    with db.engine.connect() as connection:
        lowlevel = load_low_level(mbid, offset)

        if 'artist' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['artist'] = ["[unknown]"]
        if 'release' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['release'] = ["[unknown]"]
        if 'title' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['title'] = ["[unknown]"]

        lowlevel['metadata']['audio_properties']['length_formatted'] = \
            time.strftime("%M:%S", time.gmtime(lowlevel['metadata']['audio_properties']['length']))

        summary['lowlevel'] = lowlevel

        try:
            highlevel = load_high_level(mbid, offset)
            summary['highlevel'] = highlevel
        except db.exceptions.NoDataFoundException:
            pass

        return summary
