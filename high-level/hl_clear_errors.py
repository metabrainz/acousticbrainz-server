#!/usr/bin/env python

import sys
sys.path.append("../acousticbrainz")
import config
import psycopg2

conn = psycopg2.connect(config.PG_CONNECT)
cur = conn.cursor()
cur.execute("""DELETE FROM highlevel WHERE id IN (
                 SELECT hl.id 
                   FROM highlevel hl, highlevel_json hlj 
                  WHERE hl.data = hlj.id 
                    AND hlj.data::text = '{}')""")
