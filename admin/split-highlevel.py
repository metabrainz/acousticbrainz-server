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
        count = 0

        q = text(
            """SELECT ll.id AS id
                    , ll.mbid AS mbid
                    , ll.submitted AS ll_submitted
                    , ll.build_sha1 AS ll_build_sha1
                    , ll.lossless AS ll_lossless
                    , ll.data_sha256 AS ll_data_sha256
                    , ll.data::text AS ll_data

                    , hl.build_sha1 AS hl_build_sha1
                    , hl.submitted AS hl_submitted
                    , hlj.data AS hlj_data
                 FROM lowlevel ll
                 JOIN highlevel hl
                   ON ll.id = hl.id
                 JOIN highlevel_json hlj
                   ON hl.data = hlj.id
                WHERE ll.id IN :ids
             ORDER BY ll.id
            """)

        res2 = conn2.execute(q, {"ids": id_list})
        while True:
            row = res2.fetchone()
            if not row:
                break
            row = dict(row)
            print "converting", row["id"]
            with db.engine94.begin() as connection:
                db.data_migrate.migrate_low_level(connection, row)
                db.data_migrate.migrate_high_level(connection, row)


if __name__ == "__main__":
    rewrite_lowlevel()
