import db
import db.exceptions

from sqlalchemy import text

def get_lowlevel_documents():
    query = text(
            """SELECT ll.id
                , ll.gid::text
                , llj.data
             FROM lowlevel AS ll
             JOIN lowlevel_json AS llj
            USING (id)
        LEFT JOIN bigquery_lowlevel AS bqll
               ON bqll.lowlevel = ll.id
            WHERE bqll.lowlevel IS NULL
            LIMIT 10""")
    with db.engine.connect() as connection:
        result = connection.execute(query)
        return result.fetchall()


def get_highlevel_documents():
    query = text("""
            SELECT hlmo.id AS highlevel_model_id,
                   hl.mbid::text,
                   hlmo.data,
                   mo.model AS model_name,
                   version.data AS version,
                   hlm.data AS metadata,
                   bqhl.highlevel_model
              FROM highlevel_model AS hlmo
              JOIN highlevel AS hl
                ON hl.id = hlmo.highlevel
              JOIN model AS mo
                ON hlmo.model = mo.id
              JOIN version
                ON hlmo.version = version.id
              JOIN highlevel_meta AS hlm
                ON hl.id = hlm.id
         LEFT JOIN bigquery_highlevel AS bqhl
                ON bqhl.highlevel_model = hlmo.id
             WHERE bqhl.highlevel_model IS NULL
             LIMIT 10
    """)
    with db.engine.connect() as connection:
        res = []
        result = connection.execute(query)
        for row in result.fetchall():
            highlevel_model = row["highlevel_model_id"]
            mbid = row["mbid"]
            data = row["data"]
            model_name = row["model_name"]
            version = row["version"]
            meta = row["metadata"]

            data["version"] = version
            res.append((highlevel_model, mbid, {"metadata": meta, "highlevel": {model_name: data}}))

        return res



def add_lowlevel_upload_records(lowlevel_ids):
    query = text("""
        INSERT INTO bigquery_lowlevel (lowlevel) values (:lowlevel)
        """)
    with db.engine.connect() as connection:
        for id in lowlevel_ids:
            connection.execute(query, {"lowlevel": id})


def add_highlevel_upload_records(highlevel_model_ids):
    query = text("""
        INSERT INTO bigquery_highlevel (highlevel_model) values (:highlevel_model)
        """)
    with db.engine.connect() as connection:
        for id in highlevel_model_ids:
            connection.execute(query, {"highlevel_model": id})

