#!/usr/bin/env python

# Split highlevel items into one row per highlevel model
# Also split lowlevel into separate ll_json table, and
# migrate to postgres9.4 jsonb as well!

from sqlalchemy import text

import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

import config
import db
import db.data
import db.data_jsonb
import db.data_migrate

DUMP_CHUNK_SIZE = 1000

def rewrite_lowlevel():
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    db.init_db_engine94(config.SQLALCHEMY_DATABASE_URI_94)

    connection = db.engine.connect()
    res1 = connection.execute("""SELECT id FROM lowlevel ll ORDER BY mbid""")
    total = 0
    # TODO: Keep an offline counter after every `DUMP_CHUNK_SIZE` so that
    # we can restart it if failed. Update it inside the transaction so that
    # a failed insert doesn't increase it
    while True:
        id_list = res1.fetchmany(size = DUMP_CHUNK_SIZE)
        if not id_list:
            break

        id_list = tuple([ i[0] for i in id_list ])

        conn2 = db.engine.connect()
        res2 = conn2.execute(text(
            """SELECT id, mbid, submitted, build_sha1, lossless, data_sha256, data::text
               FROM lowlevel WHERE id IN :ids ORDER BY id"""),
            {"ids": id_list})
        count = 0
        while True:
            row = res2.fetchone()
            if not row:
                break
            row = dict(row)
            print "converting", row["id"]
            db.data_migrate.migrate_low_level(row)


if __name__ == "__main__":
    rewrite_lowlevel()
