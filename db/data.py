from hashlib import sha256
import logging
import copy
import time
import json
import os
import db
import db.exceptions

from sqlalchemy import text
import sqlalchemy.exc

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

STATUS_HIDDEN = 'hidden'
STATUS_EVALUATION = 'evaluation'
STATUS_SHOW = 'show'

VERSION_TYPE_LOWLEVEL = 'lowlevel'
VERSION_TYPE_HIGHLEVEL = 'highlevel'

MODEL_STATUSES = [STATUS_HIDDEN, STATUS_EVALUATION, STATUS_SHOW]

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

def insert_version(connection, data, version_type):
    # TODO: Memoise sha -> id
    norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    sha = sha256(norm_data).hexdigest()
    query = text("""
            SELECT id
              FROM version
             WHERE data_sha256=:data_sha256
               AND type=:version_type""")
    result = connection.execute(query, {"data_sha256": sha, "version_type": version_type})
    row = result.fetchone()
    if row:
        return row[0]

    result = connection.execute(
        text("""INSERT INTO version (data, data_sha256, type)
        VALUES (:data, :sha, :version_type)
        RETURNING id"""),
        {"data": norm_data, "sha": sha, "version_type": version_type}
    )
    row = result.fetchone()
    return row[0]

def write_low_level(mbid, data):

    def _get_by_data_sha256(connection, data_sha256):
        query = text("""
            SELECT id
              FROM lowlevel_json
             WHERE data_sha256 = :data_sha256
        """)
        result = connection.execute(query, {"data_sha256": data_sha256})
        return result.fetchone()

    def _insert_lowlevel(connection, mbid, build_sha1, is_lossless_submit):
        """ Insert metadata into the lowlevel table and return its id """
        query = text("""
            INSERT INTO lowlevel (mbid, build_sha1, lossless)
                 VALUES (:mbid, :build_sha1, :lossless)
              RETURNING id
        """)
        result = connection.execute(query, {"mbid": mbid,
                                            "build_sha1": build_sha1,
                                            "lossless": is_lossless_submit})
        return result.fetchone()[0]

    def _insert_lowlevel_json(connection, ll_id, data_json, data_sha256, version_id):
        """ Insert the contents of the data file, with references to
            the version and metadata"""
        query = text("""
          INSERT INTO lowlevel_json (id, data, data_sha256, version)
               VALUES (:id, :data, :data_sha256, :version)
        """)
        connection.execute(query, {"id": ll_id,
                                   "data": data_json,
                                   "data_sha256": data_sha256,
                                   "version": version_id})

    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    version = data['metadata']['version']
    build_sha1 = version['essentia_build_sha']
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()
    with db.engine.begin() as connection:
        # See if we already have this data
        existing = _get_by_data_sha256(connection, data_sha256)
        if existing:
            logging.info("Already have %s" % data_sha256)
            return

        try:
            ll_id = _insert_lowlevel(connection, mbid, build_sha1, is_lossless_submit)
            version_id = insert_version(connection, version, VERSION_TYPE_LOWLEVEL)
            _insert_lowlevel_json(connection, ll_id, data_json, data_sha256, version_id)
            logging.info("Saved %s" % mbid)
        except sqlalchemy.exc.DataError as e:
            raise db.exceptions.BadDataException(
                    "data is badly formed")

def add_model(model_name, model_version, model_status=STATUS_HIDDEN):
    if model_status not in MODEL_STATUSES:
        raise Exception("model_status must be one of %s" % ",".join(MODEL_STATUSES))
    with db.engine.begin() as connection:
        query = text(
            """INSERT INTO model (model, model_version, status)
                    VALUES (:model_name, :model_version, :model_status)
                 RETURNING id"""
        )
        result = connection.execute(query,
            {"model_name": model_name,
             "model_version": model_version,
             "model_status": model_status})
        return result.fetchone()[0]


def set_model_status(model_name, model_version, model_status):
    if model_status not in MODEL_STATUSES:
        raise Exception("model_status must be one of %s" % ",".join(MODEL_STATUSES))
    with db.engine.begin() as connection:
        query = text(
            """UPDATE model
                  SET status = :model_status
                WHERE model_name = :model_name
                  AND model_version = :model_version"""
        )
        connection.execute(query,
            {"model_name": model_name,
             "model_version": model_version,
             "model_status": model_status})

def get_model(model_name, model_version):
    with db.engine.begin() as connection:
        query = text(
            """SELECT *
                 FROM model
                WHERE model = :model_name
                  AND model_version = :model_version""")
        result = connection.execute(query,
                    {"model_name": model_name,
                     "model_version": model_version})
        return result.fetchone()

def _get_model_id(model_name, version):
    with db.engine.begin() as connection:
        query = text(
            """SELECT id
                 FROM model
                WHERE model = :model_name
                  AND model_version = :model_version""")
        result = connection.execute(query,
                    {"model_name": model_name,
                     "model_version": version})
        row = result.fetchone()
        if row:
            return row[0]
        else:
            return None

def write_high_level_item(connection, model_name, model_version, ll_id, version_id, data):
    item_norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    item_sha = sha256(item_norm_data).hexdigest()

    model_id = _get_model_id(model_name, model_version)
    if model_id is None:
        model_id = add_model(model_name, model_version)

    item_q = text(
        """INSERT INTO highlevel_model (highlevel, data, data_sha256, model, version)
                VALUES (:highlevel, :data, :data_sha256, :model, :version)""")

    connection.execute(item_q,
        {"highlevel": ll_id, "data": item_norm_data,
            "data_sha256": item_sha, "model": model_id,
            "version": version_id})

def write_high_level_meta(connection, ll_id, mbid, build_sha1, json_meta):
    check_query = text(
        """SELECT id
             FROM highlevel
            WHERE id = :id""")
    result = connection.execute(check_query, {"id": ll_id})
    if result.rowcount:
        # If this already exists, we don't need to add it
        # (new model for existing highlevel)
        return
    hl_query = text(
        """INSERT INTO highlevel (id, mbid, build_sha1)
                VALUES (:id, :mbid, :build_sha1)""")
    connection.execute(hl_query, {"id": ll_id, "mbid": mbid, "build_sha1": build_sha1})

    meta_norm_data = json.dumps(json_meta, sort_keys=True, separators=(',', ':'))
    sha = sha256(meta_norm_data).hexdigest()
    hl_meta = text(
        """INSERT INTO highlevel_meta (id, data, data_sha256)
                VALUES (:id, :data, :data_sha256)""")
    connection.execute(hl_meta, {"id": ll_id, "data": meta_norm_data, "data_sha256": sha})


def write_high_level(mbid, ll_id, data, build_sha1):
    # If the hl runner failed to run, its output is {}
    if not data:
        return

    with db.engine.begin() as connection:
        json_meta = data["metadata"]
        json_high = data["highlevel"]

        write_high_level_meta(connection, ll_id, mbid, build_sha1, json_meta)

        hl_version = json_meta["version"]["highlevel"]
        version_id = insert_version(connection, hl_version, VERSION_TYPE_HIGHLEVEL)
        model_version = hl_version["models_essentia_git_sha"]

        for model_name, data in json_high.items():
            write_high_level_item(connection, model_name, model_version, ll_id, version_id, data)

def load_low_level(mbid, offset=0):
    """Load lowlevel data with the given mbid as a dictionary.
    If no offset is given, return the first. If an offset is
    given (from 0), return the relevent item.

    Raises db.exceptions.NoDataFoundException if the mbid doesn't
    exist or if the offset is too high."""
    with db.engine.connect() as connection:
        result = connection.execute(
            """SELECT llj.data
                 FROM lowlevel ll
                 JOIN lowlevel_json llj
                   ON ll.id = llj.id
                WHERE ll.mbid = %s
             ORDER BY ll.submitted
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
        # Metadata
        result = connection.execute(
            """SELECT hlm.id
                    , hlm.data
                 FROM highlevel_meta hlm
                 JOIN lowlevel ll
                   ON ll.id = hlm.id
                WHERE ll.mbid = %s
             ORDER BY ll.submitted
               OFFSET %s""",
            (str(mbid), offset)
        )
        metarow = result.fetchone()
        if metarow is None:
            raise db.exceptions.NoDataFoundException

        hlid = metarow[0]
        metadata = metarow[1]

        # model data
        query = text(
            """select m.model
                    , hlmo.data
                    , version.data as version
                 FROM highlevel_model hlmo
                 JOIN model m
                   ON m.id = hlmo.model
                 JOIN version
                   ON version.id = hlmo.version
                WHERE hlmo.highlevel = :hlid
                  AND m.status = 'show'
            """)
        result = connection.execute(query, {"hlid": hlid})
        highlevel = {}
        for row in result.fetchall():
            model = row[0]
            data = row[1]
            version = row[2]
            data["version"] = version
            highlevel[model] = data

        return {"metadata": metadata, "highlevel": highlevel}


def count_lowlevel(mbid):
    """Count number of stored low-level submissions for a specified MBID."""
    with db.engine.connect() as connection:
        result = connection.execute(
            "SELECT count(*) FROM lowlevel WHERE mbid = %s",
            (str(mbid),)
        )
        return result.fetchone()[0]

def get_unprocessed_highlevel_documents_for_model(highlevel_model, within=None):
    """Fetch up to 100 low-level documents which have no associated
    high level data for the given module_id.
    if `within` is set, only return mbids that are in this list"""

    within_query = ""
    if within:
        within_query = "AND ll.mbid IN :within"
    with db.engine.connect() as connection:
        query = text(
            """SELECT ll.mbid::text
                    , llj.data::text
                    , ll.id
                 FROM lowlevel AS ll
                 JOIN lowlevel_json AS llj
                   ON llj.id = ll.id
            LEFT JOIN (SELECT id, highlevel
                         FROM highlevel_model
                        WHERE model=:highlevel_model) AS hlm
                   ON ll.id = hlm.highlevel
                WHERE hlm.id IS NULL
                      %s
                LIMIT 100""" % within_query)
        params = {"highlevel_model": highlevel_model}
        if within:
            params["within"] = tuple(within)
        result = connection.execute(query, params)
        docs = result.fetchall()
        return docs

def get_unprocessed_highlevel_documents():
    """Fetch up to 100 low-level documents which have no associated high level data."""
    with db.engine.connect() as connection:
        query = text(
                """SELECT ll.mbid::text
                    , llj.data::text
                    , ll.id
                 FROM lowlevel AS ll
                 JOIN lowlevel_json AS llj
                   ON llj.id = ll.id
            LEFT JOIN highlevel AS hl
                   ON ll.id = hl.id
                WHERE hl.mbid IS NULL
                LIMIT 100""")
        result = connection.execute(query)
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
