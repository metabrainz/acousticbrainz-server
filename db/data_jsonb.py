import db
import json
from hashlib import sha256

# TODO: We shouldn't do 1 row per transaction. Instead try and do 1000 or so

def migrate_low_level(old_ll_row):
    """Migrate a lowlevel row to new schema:
     - Split metadata and data into two tables
     - Some lowlevel rows may have bad data in them. We believe there
       are <20 of these items, so we're just going to delete them
    """
    # TODO: Update id sequence at the end

    id = old_ll_row["id"]
    mbid = old_ll_row["mbid"]
    build_sha1 = old_ll_row["build_sha1"]
    data_sha256 = old_ll_row["data_sha256"]
    lossless = old_ll_row["lossless"]
    data = old_ll_row["data"]
    with db.engine94.begin() as connection:

        connection.execute(
            "INSERT INTO lowlevel (id, mbid, build_sha1, lossless)"
            "VALUES (%s, %s, %s, %s)",
            (id, mbid, build_sha1, lossless)
        )

        connection.execute(
            """INSERT INTO lowlevel_json (id, data_sha256, data)
               VALUES (%s, %s, %s)""",
            (id, data_sha256, data)
        )

def migrate_high_level(hl_row, hl_json_row):

    with db.engine.begin() as connection:
        meta_norm_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        sha = sha256(norm_data).hexdigest()
        result = connection.execute(
            """INSERT INTO highlevel_meta (data, data_sha256)
                                            VALUES (%s, %s)
                                         RETURNING id""", (norm_data, sha))
        id = result.fetchone()[0]
        connection.execute("""INSERT INTO highlevel (id, mbid, build_sha1, data, submitted)
                                   VALUES (%s, %s, %s, %s, now())""",
                           (ll_id, mbid, build_sha1, id))
