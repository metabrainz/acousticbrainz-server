#!/usr/bin/env python

# Split highlevel items into one row per highlevel model
# Also split lowlevel into separate ll_json table, and
# migrate to postgres9.4 jsonb as well!

from sqlalchemy import text

import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

import config
import db
import db.data
import db.data_migrate

DUMP_CHUNK_SIZE = 1000
MIGRATE_STATUS = 0

def write_migrate_status():
    with open("migrate-status", "w") as status:
        status.write("%d" % (MIGRATE_STATUS, ))

def read_migrate_status():
    global MIGRATE_STATUS
    if os.path.exists("migrate-status"):
        status = open("migrate-status").read()
        MIGRATE_STATUS = int(status)
        status.close()
    else:
        MIGRATE_STATUS = 0

def migrate_rows(oldengine, newengine, rowids):
    conn2 = oldengine.connect()
    count = 0

    q = text(
        """SELECT ll.id AS id
                , ll.mbid AS mbid
                , ll.submitted AS ll_submitted
                , ll.build_sha1 AS ll_build_sha1
                , ll.lossless AS ll_lossless
                , ll.data_sha256 AS ll_data_sha256
                , ll.data AS ll_data

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
        with db.engine.begin() as connection:
            db.data_migrate.migrate_low_level(connection, row)
            db.data_migrate.migrate_high_level(connection, row)

    MIGRATE_STATUS = max(id_list)
    write_migrate_status()
    # Update cursor
    db.engine.execute("""SELECT setval('lowlevel_id_seq', %s)""", (MIGRATE_STATUS, ))


def rewrite_lowlevel():
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    oldengine = create_engine(config.SQLALCHEMY_DATABASE_URI_OLD, poolclass=NullPool)

    status = read_migrate_status()

    connection = oldengine.connect()
    res1 = connection.execute(
        """SELECT id FROM lowlevel ll WHERE id > %s ORDER BY id""", (status, ))
    total = 0
    while True:
        id_list = res1.fetchmany(size = DUMP_CHUNK_SIZE)
        if not id_list:
            break

        id_list = tuple([ i[0] for i in id_list ])

        # make new transaction
        try:
            migrate_rows(oldengine, db.engine, id_list)
            # commit
        except: # Database error
            # rollback
            for i in id_list:
                # new transaction
                try:
                    migrate_rows(oldengine, dbengine, (i, ))
                    # commit
                except: # Database error
                    # rollback, ignore just this one
                    pass



if __name__ == "__main__":
    rewrite_lowlevel()
