#!/usr/bin/env python

# Split highlevel items into one row per highlevel model
# Also split lowlevel into separate ll_json table, and
# migrate to postgres9.4 jsonb as well!

from sqlalchemy import text
import time

import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

import config
import db
import db.data
import db.data_migrate

DUMP_CHUNK_SIZE = 2

def write_migrate_status(thestatus):
    with open("migrate-status", "w") as status:
        status.write("%d" % (thestatus,))

def read_migrate_status():
    if os.path.exists("migrate-status"):
        with open("migrate-status") as fp:
            status = fp.read()
            thestatus = int(status)
    else:
        thestatus = 0
    return thestatus

def migrate_rows(oldengine, newconn, id_list):
    conn2 = oldengine.connect()

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
        db.data_migrate.migrate_low_level(newconn, row)
        db.data_migrate.migrate_high_level(newconn, row)

    status = max(id_list)
    write_migrate_status(status)
    # Update cursor
    db.engine.execute("""SELECT setval('lowlevel_id_seq', %s)""", (status, ))


def rewrite_lowlevel():
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    oldengine = create_engine(config.SQLALCHEMY_DATABASE_URI_OLD, poolclass=NullPool)

    status = read_migrate_status()

    connection = oldengine.connect()
    res1 = connection.execute(
        """SELECT id FROM lowlevel ll WHERE id > %s ORDER BY id""", (status, ))
    total = 0
    print "rowcount", res1.rowcount
    while True:
        id_list = res1.fetchmany(size = DUMP_CHUNK_SIZE)
        if not id_list:
            break

        id_list = tuple([ i[0] for i in id_list ])

        # make new transaction
        newconn = db.engine.connect()
        newtrans = newconn.begin()
        try:
            migrate_rows(oldengine, newconn, id_list)
            newtrans.commit()
        except: # Database error
            newtrans.rollback()
            raise
            for i in id_list:
                newtrans = newconn.begin()
                try:
                    migrate_rows(oldengine, dbengine, (i, ))
                    newtrans.commit()
                except: # Database error
                    newtrans.rollback()
                    # rollback, ignore just this one
                    pass
        print "done", DUMP_CHUNK_SIZE, "sleeping"
        #time.sleep(5)



if __name__ == "__main__":
    rewrite_lowlevel()
