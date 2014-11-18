#!/usr/bin/env python

import sys
sys.path.append("../acousticbrainz")
import psycopg2
import config
import json
from hashlib import sha256

DUMP_CHUNK_SIZE = 1000
whitelist_tags = set(json.load(open("tagwhitelist.json")))

def rewrite_lowlevel():
    conn = psycopg2.connect(config.PG_CONNECT)
    conn2 = psycopg2.connect(config.PG_CONNECT)
    conn3 = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur2 = conn2.cursor()
    cur3 = conn3.cursor()

    cur.execute("""SELECT id FROM lowlevel ll ORDER BY mbid""")
    while True:
        id_list = cur.fetchmany(size = DUMP_CHUNK_SIZE)
        if not id_list:
            break

        id_list = tuple([ i[0] for i in id_list ])

        count = 0
        cur2.execute("SELECT id, mbid, data FROM lowlevel WHERE id IN %s ORDER BY mbid", (id_list,))
        while True:
            row = cur2.fetchone()
            if not row:
                break

            id = row[0]
            mbid = row[1]
            data = row[2]
            # print mbid
            tags = data["metadata"]["tags"]
            filename = tags["file_name"]
            for k in tags.keys():
                if k not in whitelist_tags:
                    del tags[k]
            tags["file_name"] = filename
            data["metadata"]["tags"] = tags
            query = "UPDATE lowlevel SET data = %s, data_sha256 = %s WHERE id = %s"
            data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
            data_sha256 = sha256(data_json).hexdigest()

            cur3.execute(query, (data_json, data_sha256, id))

        conn3.commit()

def rewrite_highlevel():
    conn = psycopg2.connect(config.PG_CONNECT)
    conn2 = psycopg2.connect(config.PG_CONNECT)
    conn3 = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur2 = conn2.cursor()
    cur3 = conn3.cursor()

    cur.execute("""SELECT id FROM highlevel_json ORDER BY id""")
    while True:
        id_list = cur.fetchmany(size = DUMP_CHUNK_SIZE)
        if not id_list:
            break

        id_list = tuple([ i[0] for i in id_list ])

        count = 0
        cur2.execute("SELECT id, data FROM highlevel_json WHERE id IN %s ORDER BY id", (id_list,))
        while True:
            row = cur2.fetchone()
            if not row:
                break

            id = row[0]
            data = row[1]
            # print mbid
            tags = data["metadata"]["tags"]
            filename = tags["file_name"]
            for k in tags.keys():
                if k not in whitelist_tags:
                    del tags[k]
            tags["file_name"] = filename
            data["metadata"]["tags"] = tags
            query = "UPDATE highlevel_json SET data = %s, data_sha256 = %s WHERE id = %s"
            data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
            data_sha256 = sha256(data_json).hexdigest()

            cur3.execute(query, (data_json, data_sha256, id))

        conn3.commit()

# Go through the database rewriting metadata blocks to
if __name__ == "__main__":
    #rewrite_lowlevel()
    rewrite_highlevel()
