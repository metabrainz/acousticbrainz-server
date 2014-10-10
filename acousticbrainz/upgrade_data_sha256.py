#!/usr/bin/env python

from hashlib import sha256
import json
import config
import psycopg2

class DoneException(Exception):
    pass

def hash_json(data):
    return sha256(json.dumps(data, sort_keys=True, separators=(',', ':'))).hexdigest()

def process_rows():
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, data FROM lowlevel WHERE data_sha256 IS NULL LIMIT 1")
        if cur.rowcount == 0:
            raise DoneException  # Done
        for row in cur.fetchall():
           data_sha256 = hash_json(row[1])
           cur.execute("UPDATE lowlevel SET data_sha256 = %s WHERE id = %s", (data_sha256, row[0]))
           print "Updated %s sha to %s" % (row[0], data_sha256)
           conn.commit()
        return True
    finally:
        conn.rollback()
        conn.close()

def check_schema():
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT data_sha256 FROM lowlevel LIMIT 1")
        conn.commit()
        return True
    except psycopg2.ProgrammingError:
        return False
    finally:
        conn.rollback()
        conn.close()

def amend_schema():
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur.execute("ALTER TABLE lowlevel ADD COLUMN data_sha256 TEXT")
    cur.execute("CREATE INDEX data_sha256_ndx_lowlevel ON lowlevel (data_sha256)")
    conn.commit()
    conn.close()

def finalize_schema():
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur.execute("ALTER TABLE lowlevel ALTER COLUMN data_sha256 SET NOT NULL")
    conn.commit()
    conn.close()

if not check_schema():
    amend_schema()
try:
    process_rows()
except DoneException:
    finalize_schema()
