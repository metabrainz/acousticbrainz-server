#!/usr/bin/env python
import psycopg2

# Configuration
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

if __name__ == "__main__":
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur.execute("""DELETE FROM highlevel WHERE id IN (
                     SELECT hl.id
                       FROM highlevel hl, highlevel_json hlj
                      WHERE hl.data = hlj.id
                        AND hlj.data::text = '{}')""")
    conn.commit()
