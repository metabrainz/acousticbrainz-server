import copy
import json
import logging
import os
import time
from collections import defaultdict
from hashlib import sha256

import sqlalchemy.exc
from sqlalchemy import text

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


def get_failed_highlevel_submissions():
    """Get all submissions where the highlevel extractor was run but failed.
    This is characterised by a highlevel row with a missing highlevel_meta row.

    Returns:
        (List[dict]): A list of dictionaries containing lowlevel id, mbid, submission offset
    """
    with db.engine.begin() as connection:
        query = text("""
                        SELECT ll.id
                             , ll.gid::text
                             , ll.submission_offset
                          FROM lowlevel ll
                          JOIN highlevel
                         USING (id)
                     LEFT JOIN highlevel_meta
                         USING (id)
                         WHERE highlevel_meta.id is null
                      ORDER BY ll.id
                    """)

        result = connection.execute(query).fetchall()
        rows = [dict(row) for row in result]

    return rows


def remove_failed_highlevel_submissions():
    """Remove all highlevel rows with no matching highlevel_meta rows.
    These rows represent rows that failed highlevel processing. Removing the rows
    will cause them to be processed again."""

    with db.engine.connect() as connection:
        query = text("""
                    DELETE
                      FROM highlevel
                     WHERE highlevel.id
                        IN (SELECT highlevel.id
                              FROM highlevel
                         LEFT JOIN highlevel_meta
                             USING (id)
                             WHERE highlevel_meta.id is null
                           )
                    """)
        connection.execute(query)


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


def submit_low_level_data(mbid, data, gid_type):
    """Function for submitting low-level data.

    Args:
        mbid: MusicBrainz ID of the recording that corresponds to the data
            that is being submitted.
        data: Low-level data about the recording.
        gid_type: the ID type [musicbrainzid(mbid) or messybrainzid(msid)]
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
    write_low_level(mbid, data, gid_type)


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


def write_low_level(mbid, data, is_mbid):
    def _get_by_data_sha256(connection, data_sha256):
        query = text("""
            SELECT id
              FROM lowlevel_json
             WHERE data_sha256 = :data_sha256
        """)
        result = connection.execute(query, {"data_sha256": data_sha256})
        return result.fetchone()

    def _insert_lowlevel(connection, mbid, build_sha1, is_lossless_submit, gid_type, submission_offset):
        """ Insert metadata into the lowlevel table and return its id """
        query = text("""
            INSERT INTO lowlevel (gid, build_sha1, lossless, gid_type, submission_offset)
                 VALUES (:mbid, :build_sha1, :lossless, :gid_type, :submission_offset)
              RETURNING id
        """)
        result = connection.execute(query, {"mbid": mbid,
                                            "build_sha1": build_sha1,
                                            "lossless": is_lossless_submit,
                                            "gid_type": gid_type,
                                            "submission_offset": submission_offset})
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
            submission_offset = get_next_submission_offset(connection, mbid)
            ll_id = _insert_lowlevel(connection, mbid, build_sha1, is_lossless_submit, is_mbid, submission_offset)
            version_id = insert_version(connection, version, VERSION_TYPE_LOWLEVEL)
            _insert_lowlevel_json(connection, ll_id, data_json, data_sha256, version_id)
            logging.info("Saved %s" % mbid)
        except sqlalchemy.exc.DataError as e:
            raise db.exceptions.BadDataException(
                "data is badly formed")


def get_next_submission_offset(connection, mbid):
    """Get highest existing submission offset for mbid, then increment.
    If the mbid doesn't exist in the database, return an offset of 0"""
    query = text("""
        SELECT MAX(submission_offset) as max_offset
          FROM lowlevel
         WHERE gid = :mbid
    """)
    result = connection.execute(query, {"mbid": mbid})

    row = result.fetchone()
    if row["max_offset"] is not None:
        return row["max_offset"] + 1
    else:
        # No previous submission
        return 0


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
                WHERE model = :model_name
                  AND model_version = :model_version"""
        )
        connection.execute(query,
                           {"model_name": model_name,
                            "model_version": model_version,
                            "model_status": model_status})


def get_active_models():
    with db.engine.begin() as connection:
        query = text(
            """SELECT *
                 FROM model
                WHERE status = :model_status""")
        result = connection.execute(query,
                                    {"model_status": STATUS_SHOW})
        return [dict(row) for row in result.fetchall()]


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

    if json_meta:
        meta_norm_data = json.dumps(json_meta, sort_keys=True, separators=(',', ':'))
        sha = sha256(meta_norm_data).hexdigest()
        hl_meta = text(
            """INSERT INTO highlevel_meta (id, data, data_sha256)
                    VALUES (:id, :data, :data_sha256)""")
        connection.execute(hl_meta, {"id": ll_id, "data": meta_norm_data, "data_sha256": sha})


def write_high_level(mbid, ll_id, data, build_sha1):
    """Write highlevel data to the database.

    This includes entries in the
      highlevel
      version
      highlevel_model
    tables. If the exact version already exists it will be reused.

    If `data` is an empty dictionary, a highlevel table entry is still recorded
    so that this submission is no longer processed by the highlevel runner
    """
    with db.engine.begin() as connection:
        json_meta = data.get("metadata", {})
        json_high = data.get("highlevel", {})

        write_high_level_meta(connection, ll_id, mbid, build_sha1, json_meta)

        if json_meta and json_high:
            hl_version = json_meta["version"]["highlevel"]
            version_id = insert_version(connection, hl_version, VERSION_TYPE_HIGHLEVEL)
            model_version = hl_version["models_essentia_git_sha"]

            for model_name, data in json_high.items():
                write_high_level_item(connection, model_name, model_version, ll_id, version_id, data)


def load_low_level(mbid, offset=0):
    """Load lowlevel data with the given mbid as a dictionary.
    If no offset is given, return the first. If an offset is
    given (from 0), return the relevent item.

    Arguments:
        mbid (str): MBID to load
        offset (int): submission offset for this MBID, starting from 0

    Raises:
        NoDataFoundException: if this mbid doesn't exist or the offset is too high"""

    # in case it's a uuid
    mbid = str(mbid).lower()
    result = load_many_low_level([(mbid, offset)])
    if not result:
        raise db.exceptions.NoDataFoundException

    return result[mbid][str(offset)]


def load_many_low_level(recordings):
    """Collect low-level JSON data for multiple recordings.

    Args:
        recordings: A list of tuples (mbid, offset).

    Returns:
        A dictionary of mbids containing a dictionary of offsets. If an (mbid, offset) doesn't exist
        in the database, it is ommitted from the returned data.

        {"mbid-1": {"offset-1": lowlevel_data,
                    ...
                    "offset-n": lowlevel_data},
         ...
         "mbid-n": {"offset-1": lowlevel_data}
        }

    """
    with db.engine.connect() as connection:
        query = text("""
            SELECT ll.gid::text,
                   ll.submission_offset::text,
                   llj.data
              FROM lowlevel ll
              JOIN lowlevel_json llj
                ON ll.id = llj.id
             WHERE (ll.gid, ll.submission_offset) 
                IN :recordings
        """)

        result = connection.execute(query, {'recordings': tuple(recordings)})

        recordings_info = defaultdict(dict)
        for row in result.fetchall():
            recordings_info[row['gid']][row['submission_offset']] = row['data']

        return dict(recordings_info)


def map_highlevel_class_names(highlevel, mapping):
    """Convert class names from the classifier output to human readable names.

    Arguments:
        highlevel (dict): highlevel data dict containing shortened keys
        mapping (dict): a mapping from class names -> human readable names

    Returns:
        the highlevel input with the keys of the `all` item, and the `value` item
        changed to the values from the provided mapping
    """

    new_all = {}
    for cl, val in highlevel["all"].items():
        new_all[mapping[cl]] = val
    highlevel["all"] = new_all
    highlevel["value"] = mapping[highlevel["value"]]

    return highlevel


def load_high_level(mbid, offset=0, map_classes=False):
    """Load high-level data for a given MBID.

    Arguments:
        mbid (str): MBID to load
        offset (int): submission offset for this MBID, starting from 0
        map_classes (bool): if True, map class names to human readable values in the returned data

    Raises:
        NoDataFoundException: if this mbid doesn't exist or the offset is too high
    """

    # in case it's a uuid
    mbid = str(mbid).lower()
    result = load_many_high_level([(mbid, offset)], map_classes)
    if not result:
        raise db.exceptions.NoDataFoundException

    return result[mbid][str(offset)]


def load_many_high_level(recordings, map_classes=False):
    """Collect high-level data for multiple recordings.

    Args:
        recordings: A list of tuples (mbid, offset).
        map_classes (bool): if True, map class names to human readable values in the returned data

    Returns:
        {"mbid-1": {"offset-1": {"metadata-1": metadata, "highlevel-1": highlevel},
                    ...
                    "offset-n": {"metadata-n": metadata, "highlevel-n": highlevel}},
         ...
         "mbid-n": {"offset-1": {"metadata-1": metadata, "highlevel-1": highlevel}}
        }

    """
    with db.engine.connect() as connection:
        # Metadata
        meta_query = text("""
            SELECT hl.id
                 , hlm.data
                 , ll.gid::text
                 , ll.submission_offset::text
              FROM highlevel hl
              JOIN highlevel_meta hlm
                ON hl.id = hlm.id
              JOIN lowlevel ll
                ON ll.id = hl.id
             WHERE (ll.gid, ll.submission_offset)
                IN :recordings
        """)

        meta_result = connection.execute(meta_query, {'recordings': tuple(recordings)})
        # Return empty dictionary if no metadata is found
        if not meta_result.rowcount:
            return {}

        hlids = []
        recordings_info = defaultdict(dict)
        for row in meta_result.fetchall():
            hlids.append(row['id'])
            gid = row['gid']
            submission_offset = row['submission_offset']
            recordings_info[gid][submission_offset] = {'metadata': row['data'],
                                                       'highlevel': {}}

        # Model data
        model_query = text("""
            SELECT m.model
                 , hlmo.data
                 , version.data as version
                 , ll.gid::text
                 , ll.submission_offset::text
                 , m.class_mapping
              FROM highlevel_model hlmo
              JOIN model m
                ON m.id = hlmo.model
              JOIN version
                ON version.id = hlmo.version
              JOIN lowlevel ll
                ON ll.id = hlmo.highlevel
             WHERE hlmo.highlevel IN :hlids
               AND m.status = 'show'
        """)

        model_result = connection.execute(model_query, {'hlids': tuple(hlids)})
        for row in model_result.fetchall():
            model = row['model']
            data = row['data']
            mapping = row['class_mapping']
            if map_classes and mapping:
                data = map_highlevel_class_names(data, mapping)

            data['version'] = row['version']

            gid = row['gid']
            submission_offset = row['submission_offset']
            recordings_info[gid][submission_offset]['highlevel'][model] = data

        return dict(recordings_info)


def get_mbids_by_ids(ids):
    # Get (MBID, offset) combinations for a list of lowlevel.ids
    with db.engine.connect() as connection:
        query = text("""
            SELECT id
                 , gid
                 , submission_offset
              FROM lowlevel
             WHERE id IN :ids
        """)
        result = connection.execute(query, {"ids": tuple(ids)})

        recordings = []
        for row in result.fetchall():
            recordings.append((str(row["gid"]), row["submission_offset"]))

        return recordings


# I noticed that we usually only do things by (MBID, offset), not id - should this work match that pattern?
def get_lowlevel_metric_feature(id, path):
    # Get lowlevel data only for a specified path.
    try:
        id = int(id)
    except ValueError:
        raise db.exceptions.BadDataException("The parameter `id` must be an integer.")

    with db.engine.connect() as connection:
        query = text("""
            SELECT id, %(path)s AS data
              FROM lowlevel_json
             WHERE id = :id
        """ % {"path": path})
        result = connection.execute(query, {'id': id})
        if not result.rowcount:
            # No data for specified id
            return None
        row = result.fetchone()
        return row["data"]


def get_lowlevel_by_id(id):
    # Get lowlevel data for a specific id.
    try:
        id = int(id)
    except ValueError:
        raise db.exceptions.BadDataException('Parameter `id` must be an integer.')
    
    with db.engine.connect() as connection:
        query = text("""
            SELECT id, data
              FROM lowlevel_json
             WHERE id = :id
        """)
        result = connection.execute(query, {"id": id})
        if not result.rowcount:
            return None
        return result.fetchone()["data"]


def get_highlevel_models(id):
    """Get highlevel model data for a specified id.

    Args:
        id: integer, indicating the highlevel_model.highlevel
        or the corresponding lowlevel.id for a submission.

    Returns: highlevel models aggregated with their names,
    a dictionary of the form:
        {
            "model_1": {model_document},
            ...,
            "model_n": {model_document}
        }
    """
    try:
        id = int(id)
    except ValueError:
        raise db.exceptions.BadDataException("The parameter `id` must be an integer.")

    with db.engine.connect() as connection:
        query = text("""
            SELECT jsonb_object_agg(model.model, hlm.data) AS data
              FROM highlevel_model AS hlm
         LEFT JOIN model
                ON model.id = hlm.model
             WHERE highlevel = :id
               AND model.status = 'show'
          GROUP BY highlevel
        """)
        result = connection.execute(query, {"id": id})
        if not result.rowcount:
            return None
        row = result.fetchone()
        return row["data"]


def get_lowlevel_id(mbid, offset):
    # Get lowlevel.id for (MBID, offset)
    mbid = str(mbid).lower()
    with db.engine.connect() as connection:
        query = text("""
            SELECT id
            FROM lowlevel
            WHERE gid = :mbid AND submission_offset = :offset
        """)
        result = connection.execute(query, {"mbid": mbid, "offset": offset})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException('No data exists for the (MBID, offset) pair specified')
        return result.fetchone()["id"]


def check_for_submission(id):
    # Check that a submission with the given lowlevel.id exists
    with db.engine.connect() as connection:
        query = text("""
                    SELECT *
                      FROM lowlevel
                     WHERE id = :id
                """)
        result = connection.execute(query, {"id": id})
        if not result.rowcount:
            return False
        return True


def count_all_lowlevel():
    """Get total number of low-level submissions"""
    with db.engine.connect() as connection:
        query = text("""
            SELECT COUNT(*)
            FROM lowlevel
        """)
        result = connection.execute(query)
        return result.fetchone()[0]


def count_lowlevel(mbid):
    """Count number of stored low-level submissions for a specified MBID."""
    with db.engine.connect() as connection:
        result = connection.execute(
            """SELECT COUNT(*)
                 FROM lowlevel
                WHERE gid = %s""",
            (str(mbid),)
        )
        return result.fetchone()[0]


def count_many_lowlevel(mbids):
    """Count number of stored low-level submissions for a specified set
    of MBID."""
    with db.engine.connect() as connection:
        query = text(
            """SELECT gid
                    , COUNT(*)
                 FROM lowlevel
                WHERE gid IN :mbids
             GROUP BY gid""")
        return {str(mbid): {"count": int(count)} for mbid, count
                in connection.execute(query, {"mbids": tuple(mbids)})}


def get_unprocessed_highlevel_documents_for_model(highlevel_model, within=None):
    """Fetch up to 100 low-level documents which have no associated
    high level data for the given module_id.
    if `within` is set, only return mbids that are in this list"""

    within_query = ""
    if within:
        within_query = "AND ll.mbid IN :within"
    with db.engine.connect() as connection:
        query = text(
            """SELECT ll.gid::text
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
            """SELECT ll.gid::text
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
        mbid: musicbrainz id to get data for
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
        models = get_active_models()
        summary['models'] = models
    except db.exceptions.NoDataFoundException:
        pass

    return summary
