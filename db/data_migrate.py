import db
import json
from hashlib import sha256
from sqlalchemy import text

VERSION_TYPE_LOWLEVEL = 'lowlevel'
VERSION_TYPE_HIGHLEVEL = 'highlevel'

version_cache = {}

def insert_version(connection, data, version_type):
    # TODO: Memoise sha -> id
    norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    sha = sha256(norm_data).hexdigest()
    if sha in version_cache:
        return version_cache[sha]

    query = text("""
            SELECT id
              FROM version
             WHERE data_sha256=:data_sha256
               AND type=:version_type""")
    result = connection.execute(query, {"data_sha256": sha, "version_type": version_type})
    row = result.fetchone()
    if row:
        version_cache[sha] = row[0]
        return row[0]

    result = connection.execute(
        text("""INSERT INTO version (data, data_sha256, type)
        VALUES (:data, :sha, :version_type)
        RETURNING id"""),
        {"data": norm_data, "sha": sha, "version_type": version_type}
    )
    row = result.fetchone()
    version_cache[sha] = row[0]
    return row[0]


def migrate_low_level(connection, old_ll_row):
    """Migrate a lowlevel row to new schema:
     - Split metadata and data into two tables
     - Some lowlevel rows may have bad data in them. We believe there
       are <20 of these items, so we're just going to delete them
    """
    id = old_ll_row["id"]
    mbid = old_ll_row["mbid"]
    build_sha1 = old_ll_row["ll_build_sha1"]
    data_sha256 = old_ll_row["ll_data_sha256"]
    lossless = old_ll_row["ll_lossless"]
    submitted = old_ll_row["ll_submitted"]
    data = old_ll_row["ll_data"]

    norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    sha = sha256(norm_data).hexdigest()

    if sha != data_sha256:
        raise Exception("Stored sha should be the same as computed sha, but isn't")
    ll_version = data["metadata"]["version"]
    version_id = insert_version(connection, ll_version, VERSION_TYPE_LOWLEVEL)

    connection.execute(
        "INSERT INTO lowlevel (id, gid, build_sha1, lossless, submitted)"
        "VALUES (%s, %s, %s, %s, %s)",
        (id, mbid, build_sha1, lossless, submitted)
    )

    connection.execute(
        """INSERT INTO lowlevel_json (id, data_sha256, data, version)
           VALUES (%s, %s, %s, %s)""",
        (id, data_sha256, norm_data, version_id)
    )

def _get_model_id(name):
    models = {u'danceability': 1,
     u'gender': 2,
     u'genre_dortmund': 3,
     u'genre_electronic': 4,
     u'genre_rosamerica': 5,
     u'genre_tzanetakis': 6,
     u'ismir04_rhythm': 7,
     u'mood_acoustic': 8,
     u'mood_aggressive': 9,
     u'mood_electronic': 10,
     u'mood_happy': 11,
     u'mood_party': 12,
     u'mood_relaxed': 13,
     u'mood_sad': 14,
     u'moods_mirex': 15,
     u'timbre': 16,
     u'tonal_atonal': 17,
     u'voice_instrumental': 18}
    return models[name]

def migrate_high_level(connection, hl_row):

    highlevel_id = hl_row["id"]
    mbid = hl_row["mbid"]
    build_sha1 = hl_row["hl_build_sha1"]
    submitted = hl_row["hl_submitted"]

    hl_json = hl_row["hlj_data"]

    hl_query = text(
        """INSERT INTO highlevel (id, gid, build_sha1, submitted)
                VALUES (:id, :mbid, :build_sha1, :submitted)""")
    connection.execute(hl_query, {"id": highlevel_id, "mbid": mbid,
        "build_sha1": build_sha1, "submitted": submitted})

    # If the hl runner failed to run, we put {}
    # in the database
    if not hl_json:
        return

    json_meta = hl_json["metadata"]
    json_high = hl_json["highlevel"]

    meta_norm_data = json.dumps(json_meta, sort_keys=True, separators=(',', ':'))
    sha = sha256(meta_norm_data).hexdigest()
    hl_meta = text(
        """INSERT INTO highlevel_meta (id, data, data_sha256)
                VALUES (:id, :data, :data_sha256)""")
    connection.execute(hl_meta, {"id": highlevel_id, "data": meta_norm_data, "data_sha256": sha})
    hl_version = json_meta["version"]["highlevel"]
    version_id = insert_version(connection, hl_version, VERSION_TYPE_HIGHLEVEL)

    for name, data in json_high.items():
        item_norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        item_sha = sha256(item_norm_data).hexdigest()

        # For a migration we know the existing models, this is faster
        # than 50 million sql queries to get 18 known values
        model_id = _get_model_id(name)

        item_q = text(
            """INSERT INTO highlevel_model (highlevel, data, data_sha256, model, version)
                    VALUES (:highlevel, :data, :data_sha256, :model, :version)""")

        connection.execute(item_q,
            {"highlevel": highlevel_id, "data": item_norm_data,
                "data_sha256": item_sha, "model": model_id,
                "version": version_id})
