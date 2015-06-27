#!/usr/bin/env python
import psycopg2

# Configuration
import sys
sys.path.append("..")
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
