import db
from brainzutils import musicbrainz_db
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def load_artist_credit(connection, gids_in_AB):
    artist_credit_query = text("""
        SELECT DISTINCT artist_credit.id, artist_credit.name, artist_credit.artist_count,
                artist_credit.ref_count, artist_credit.created
                FROM artist_credit
                INNER JOIN recording
                ON artist_credit.id = recording.artist_credit
                WHERE recording.gid in :gids OR artist_credit.id in :data
    """)
    MB_release_fk_artist_credit = []
    for value in MB_release_data:
        MB_release_fk_artist_credit.append(value[3])
    MB_release_fk_artist_credit = list(set(MB_release_fk_artist_credit))

    result = connection.execute(artist_credit_query, {'gids': tuple(gids_in_AB), 'data': tuple(MB_release_fk_artist_credit)})
    global MB_artist_credit_data
    MB_artist_credit_data = result.fetchall()


def load_artist_type(connection, gids_in_AB):
    artist_type_query = text("""
        SELECT DISTINCT artist_type.id,
                artist_type.name,
                artist_type.parent,
                artist_type.child_order,
                artist_type.description,
                artist_type.gid
          FROM artist_type
    INNER JOIN artist
            ON artist.type = artist_type.id
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(artist_type_query, {'gids': tuple(gids_in_AB)})
    global MB_artist_type_data
    MB_artist_type_data = result.fetchall()


def load_area_type(connection, gids_in_AB):
    area_type_query =   text("""
        SELECT DISTINCT area_type.id,
               area_type.name,
               area_type.parent,
               area_type.child_order,
               area_type.description,
               area_type.gid
          FROM area_type
    INNER JOIN area
            ON area.type = area_type.id
    INNER JOIN artist
            ON area.id = artist.area
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(area_type_query, {'gids': tuple(gids_in_AB)})
    global MB_area_type_data
    MB_area_type_data = result.fetchall()


def load_begin_area_type(connection, gids_in_AB):
    begin_area_type_query =   text("""
        SELECT DISTINCT area_type.id,
               area_type.name,
               area_type.parent,
               area_type.child_order,
               area_type.description,
               area_type.gid
          FROM area_type
    INNER JOIN area
            ON area.type = area_type.id
    INNER JOIN artist
            ON area.id = artist.begin_area
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(begin_area_type_query, {'gids': tuple(gids_in_AB)})
    global MB_begin_area_type_data
    MB_begin_area_type_data = result.fetchall()


def load_end_area_type(connection, gids_in_AB):
    end_area_type_query =   text("""
        SELECT DISTINCT area_type.id,
               area_type.name,
               area_type.parent,
               area_type.child_order,
               area_type.description,
               area_type.gid
          FROM area_type
    INNER JOIN area
            ON area.type = area_type.id
    INNER JOIN artist
            ON area.id = artist.end_area
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(end_area_type_query, {'gids': tuple(gids_in_AB)})
    global MB_end_area_type_data
    MB_end_area_type_data = result.fetchall()


def load_release_status(connection, gids_in_AB):
    release_status_query = text("""
        SELECT DISTINCT release_status.id,
               release_status.name,
               release_status.parent,
               release_status.child_order,
               release_status.description,
               release_status.gid
          FROM release_status
    INNER JOIN release
            ON release.status = release_status.id
    INNER JOIN recording
            ON recording.artist_credit = release.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(release_status_query, {'gids': tuple(gids_in_AB)})
    global MB_release_status_data
    MB_release_status_data = result.fetchall()


def load_release_group_primary_type(connection, gids_in_AB):
    release_group_primary_type_query = text("""
        SELECT DISTINCT release_group_primary_type.id, release_group_primary_type.name,
               release_group_primary_type.parent, release_group_primary_type.child_order,
               release_group_primary_type.description, release_group_primary_type.gid
        FROM release_group_primary_type INNER JOIN release_group
        ON release_group_primary_type.id = release_group.type
        INNER JOIN recording
                ON recording.artist_credit = release_group.artist_credit
             WHERE recording.gid in :gids OR release_group_primary_type.id in :data
    """)
    MB_release_group_fk_type = []
    for value in MB_release_group_data:
        MB_release_group_fk_type.append(value[4])
    MB_release_group_fk_type = list(set(MB_release_group_fk_type))

    result = connection.execute(release_group_primary_type_query, {'gids': tuple(gids_in_AB), 'data': tuple(MB_release_group_fk_type)})
    global MB_release_group_primary_type_data
    MB_release_group_primary_type_data = result.fetchall()


def load_medium_format(connection, gids_in_AB):
    medium_format_query = text("""
        SELECT * FROM medium_format
        ORDER BY id
    """)
    result = connection.execute(medium_format_query)
    global MB_medium_format_data
    MB_medium_format_data = result.fetchall()


def load_release_packaging(connection, gids_in_AB):
    release_packaging_query = text("""
        SELECT DISTINCT release_packaging.id,
               release_packaging.name,
               release_packaging.parent,
               release_packaging.child_order,
               release_packaging.description,
               release_packaging.gid
          FROM release_packaging
    INNER JOIN release
            ON release.packaging = release_packaging.id
    INNER JOIN recording
            ON recording.artist_credit = release.artist_credit
         WHERE recording.gid in :gids OR release_packaging.id in :data
    """)
    MB_release_fk_packaging = []
    for value in MB_release_data:
        MB_release_fk_packaging.append(value[6])
    MB_release_fk_packaging = list(set(MB_release_fk_packaging))

    result = connection.execute(release_packaging_query, {'gids': tuple(gids_in_AB), 'data': tuple(MB_release_fk_packaging)})
    global MB_release_packaging_data
    MB_release_packaging_data = result.fetchall()


def load_language(connection, gids_in_AB):
    language_query = text("""
        SELECT DISTINCT language.id,
               language.iso_code_2t,
               language.iso_code_2b,
               language.iso_code_1,
               language.name,
               language.frequency,
               language.iso_code_3
          FROM language
    INNER JOIN release
            ON release.language = language.id
    INNER JOIN recording
            ON recording.artist_credit=release.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(language_query, {'gids': tuple(gids_in_AB)})
    global MB_language_data
    MB_language_data = result.fetchall()


def load_script(connection, gids_in_AB):
    script_query = text("""
        SELECT DISTINCT script.id,
               script.iso_code,
               script.iso_number,
               script.name,
               script.frequency
          FROM script
    INNER JOIN release
            ON release.script = script.id
    INNER JOIN recording
            ON recording.artist_credit = release.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(script_query, {'gids': tuple(gids_in_AB)})
    global MB_script_data
    MB_script_data = result.fetchall()


def load_gender(connection, gids_in_AB):
    gender_query = text("""
        SELECT DISTINCT gender.id,
               gender.name,
               gender.parent,
               gender.child_order,
               gender.description,
               gender.gid
          FROM gender
    INNER JOIN artist
            ON artist.gender = gender.id
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(gender_query, {'gids': tuple(gids_in_AB)})
    global MB_gender_data
    MB_gender_data = result.fetchall()


def load_area(connection, gids_in_AB):
    area_query = text("""
        SELECT DISTINCT area.id,
               area.gid,
               area.name,
               area.type,
               area.edits_pending,
               area.last_updated,
               area.begin_date_year,
               area.begin_date_month,
               area.begin_date_day,
               area.end_date_year,
               area.end_date_month,
               area.end_date_day,
               area.ended,
               area.comment
          FROM area
    INNER JOIN artist
            ON area.id = artist.area
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(area_query, {'gids': tuple(gids_in_AB)})
    global MB_area_data
    MB_area_data = result.fetchall()


def load_begin_area(connection, gids_in_AB):
    begin_area_query = text("""
        SELECT DISTINCT area.id,
               area.gid,
               area.name,
               area.type,
               area.edits_pending,
               area.last_updated,
               area.begin_date_year,
               area.begin_date_month,
               area.begin_date_day,
               area.end_date_year,
               area.end_date_month,
               area.end_date_day,
               area.ended,
               area.comment
          FROM area
    INNER JOIN artist
            ON area.id = artist.begin_area
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids OR area.id in :data
    """)
    MB_artist_fk_begin_area = []
    for value in MB_artist_data:
        MB_artist_fk_begin_area.append(value[17])

    result = connection.execute(begin_area_query, {'gids': tuple(gids_in_AB), 'data': tuple(MB_artist_fk_begin_area)})
    global MB_begin_area_data
    MB_begin_area_data = result.fetchall()


def load_end_area(connection, gids_in_AB):
    end_area_query = text("""
        SELECT DISTINCT area.id,
               area.gid,
               area.name,
               area.type,
               area.edits_pending,
               area.last_updated,
               area.begin_date_year,
               area.begin_date_month,
               area.begin_date_day,
               area.end_date_year,
               area.end_date_month,
               area.end_date_day,
               area.ended,
               area.comment
          FROM area
    INNER JOIN artist
            ON area.id = artist.end_area
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(end_area_query, {'gids': tuple(gids_in_AB)})
    global MB_end_area_data
    MB_end_area_data = result.fetchall()


def load_artist_credit_name(connection, gids_in_AB):
    artist_credit_name_query = text("""
        SELECT DISTINCT artist_credit_name.artist_credit,
               artist_credit_name.position,
               artist_credit_name.artist,
               artist_credit_name.name,
               artist_credit_name.join_phrase
          FROM artist_credit_name
    INNER JOIN artist_credit
            ON artist_credit_name.artist_credit = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(artist_credit_name_query, {'gids': tuple(gids_in_AB)})
    global MB_artist_credit_name_data
    MB_artist_credit_name_data = result.fetchall()


def load_artist(connection, gids_in_AB):
    artist_query = text("""
        SELECT DISTINCT artist.id, artist.gid, artist.name, artist.sort_name, artist.begin_date_year,
               artist.begin_date_month, artist.begin_date_day, artist.end_date_year, artist.end_date_month,
               artist.end_date_day, artist.type, artist.area, artist.gender, artist.comment, artist.edits_pending,
               artist.last_updated, artist.ended, artist.begin_area, artist.end_area
          FROM artist
    INNER JOIN artist_credit
            ON artist_credit.id = artist.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids OR artist.id in :data
    """)
    MB_artist_credit_name_fk_artist = []
    for value in MB_artist_credit_name_data:
        MB_artist_credit_name_fk_artist.append(value[2])

    result = connection.execute(artist_query, {'gids': tuple(gids_in_AB), 'data': tuple(MB_artist_credit_name_fk_artist)})
    global MB_artist_data
    MB_artist_data = result.fetchall()


def load_artist_gid_redirect(connection, gids_in_AB):
    artist_gid_redirect_query = text("""
        SELECT DISTINCT artist_gid_redirect.gid,
               artist_gid_redirect.new_id,
               artist_gid_redirect.created
          FROM artist_gid_redirect
    INNER JOIN artist
            ON artist.id = artist_gid_redirect.new_id
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
    INNER JOIN recording
            ON artist_credit.id = recording.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(artist_gid_redirect_query, {'gids': tuple(gids_in_AB)})
    global MB_artist_gid_redirect_data
    MB_artist_gid_redirect_data = result.fetchall()


def load_recording(connection, gids_in_AB):
    recording_query = text("""
        SELECT DISTINCT recording.id, recording.gid, recording.name, recording.artist_credit,
               recording.length, recording.comment, recording.edits_pending, recording.last_updated,
               recording.video
         FROM  recording
        WHERE  recording.gid in :gids
    """)
    result = connection.execute(recording_query, {'gids': tuple(gids_in_AB)})
    global MB_recording_data
    MB_recording_data = result.fetchall()


def load_recording_gid_redirect(connection, gids_in_AB):
    recording_gid_redirect_query = text("""
        SELECT DISTINCT recording_gid_redirect.gid,
               recording_gid_redirect.new_id,
               recording_gid_redirect.created
          FROM recording_gid_redirect
    INNER JOIN recording
            ON recording.id = recording_gid_redirect.new_id
         WHERE recording.gid in :gids
    """)
    result = connection.execute(recording_gid_redirect_query, {'gids': tuple(gids_in_AB)})
    global MB_recording_gid_redirect_data
    MB_recording_gid_redirect_data = result.fetchall()


def load_release_group(connection, gids_in_AB):
    release_group_query = text("""
        SELECT DISTINCT release_group.id,
               release_group.gid,
               release_group.name,
               release_group.artist_credit,
               release_group.type,
               release_group.comment,
               release_group.edits_pending,
               release_group.last_updated
          FROM release_group
    INNER JOIN recording
            ON recording.artist_credit = release_group.artist_credit
         WHERE recording.gid in :gids OR release_group.id in :redirect_data OR release_group.id in :release_data
    """)
    MB_release_group_gid_redirect_fk_release_group = []
    for value in MB_release_group_gid_redirect_data:
        MB_release_group_gid_redirect_fk_release_group.append(value[1])
    MB_release_group_gid_redirect_fk_release_group = list(set(MB_release_group_gid_redirect_fk_release_group))

    MB_release_fk_release_group = []
    for value in MB_release_data:
        MB_release_fk_release_group.append(value[4])
    MB_release_fk_release_group = list(set(MB_release_fk_release_group))

    result = connection.execute(release_group_query, {'gids': tuple(gids_in_AB),
                                                      'redirect_data': tuple(MB_release_group_gid_redirect_fk_release_group),
                                                      'release_data': tuple(MB_release_fk_release_group)})
    global MB_release_group_data
    MB_release_group_data = result.fetchall()


def load_release_group_gid_redirect(connection, gids_in_AB):
    release_group_gid_redirect_query = text("""
        SELECT DISTINCT release_group_gid_redirect.gid,
               release_group_gid_redirect.new_id,
               release_group_gid_redirect.created
          FROM release_group_gid_redirect
    INNER JOIN release_group
            ON release_group.id = release_group_gid_redirect.new_id
    INNER JOIN recording
            ON recording.artist_credit = release_group.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(release_group_gid_redirect_query, {'gids': tuple(gids_in_AB)})
    global MB_release_group_gid_redirect_data
    MB_release_group_gid_redirect_data = result.fetchall()


def load_release(connection, gids_in_AB):
    release_query = text("""
        SELECT DISTINCT release.id,
               release.gid,
               release.name,
               release.artist_credit,
               release.release_group,
               release.status,
               release.packaging,
               release.language,
               release.script,
               release.barcode,
               release.comment,
               release.edits_pending,
               release.quality,
               release.last_updated
          FROM release
    INNER JOIN recording
            ON recording.artist_credit = release.artist_credit
         WHERE recording.gid in :gids OR release.id in :medium_data OR release.id in :redirect_data
    """)
    MB_medium_fk_release = []
    for value in MB_medium_data:
        MB_medium_fk_release.append(value[1])
    MB_medium_fk_release = list(set(MB_medium_fk_release))

    MB_release_gid_redirect_fk_release = []
    for value in MB_release_gid_redirect_data:
        MB_release_gid_redirect_fk_release.append(value[1])
    MB_release_gid_redirect_fk_release = list(set(MB_release_gid_redirect_fk_release))

    result = connection.execute(release_query, {'gids': tuple(gids_in_AB),
                                                'medium_data': tuple(MB_medium_fk_release),
                                                'redirect_data': tuple(MB_release_gid_redirect_fk_release)
                                               })
    global MB_release_data
    MB_release_data = result.fetchall()


def load_release_gid_redirect(connection, gids_in_AB):
    release_gid_redirect_query = text("""
        SELECT DISTINCT release_gid_redirect.gid,
               release_gid_redirect.new_id,
               release_gid_redirect.created
          FROM release_gid_redirect
    INNER JOIN release
            ON release.id = release_gid_redirect.new_id
    INNER JOIN recording
            ON recording.artist_credit = release.artist_credit
         WHERE recording.gid in :gids
    """)
    result = connection.execute(release_gid_redirect_query, {'gids': tuple(gids_in_AB)})
    global MB_release_gid_redirect_data
    MB_release_gid_redirect_data = result.fetchall()


def load_medium(connection, gids_in_AB):
    medium_query = text("""
        SELECT DISTINCT medium.id,
               medium.release,
               medium.position,
               medium.format,
               medium.name,
               medium.edits_pending,
               medium.last_updated,
               medium.track_count
          FROM medium
    INNER JOIN release
            ON release.id = medium.release
    INNER JOIN recording
            ON recording.artist_credit=release.artist_credit
         WHERE recording.gid in :gids OR medium.id in :data
    """)
    MB_track_fk_medium = []
    for value in MB_track_data:
        MB_track_fk_medium.append(value[3])

    result = connection.execute(medium_query, {'gids': tuple(gids_in_AB), 'data': tuple(MB_track_fk_medium)})
    global MB_medium_data
    MB_medium_data = result.fetchall()


def load_track(connection, gids_in_AB):
    track_query = text("""
        SELECT DISTINCT track.id,
               track.gid,
               track.recording,
               track.medium,
               track.position,
               track.number,
               track.name,
               track.artist_credit,
               track.length,
               track.edits_pending,
               track.last_updated,
               track.is_data_track
          FROM track
    INNER JOIN recording
            ON track.recording = recording.id
         WHERE recording.gid in :gids
    """)
    result = connection.execute(track_query, {'gids': tuple(gids_in_AB)})
    global MB_track_data
    MB_track_data = result.fetchall()


print("--------------------------------------------------------------------------------------------------")


# TO ACOUSTICBRAINZ
def write_artist_credit(transaction, connection):
    artist_credit_query = text("""
        INSERT INTO musicbrainz.artist_credit
            VALUES (:id, :name, :artist_count, :ref_count, :created)
    """)
    values = [{
        "id" : value[0],
        "name" : value[1],
        "artist_count" : value[2],
        "ref_count" : value[3],
        "created" : value[4]} for value in MB_artist_credit_data
    ]
    connection.execute(artist_credit_query, values)
    transaction.commit()
    print("INSERTED artist_credit data\n")


def write_artist_type(transaction, connection):
    artist_type_query = text("""
        INSERT INTO musicbrainz.artist_type
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name" : value[01],
        "parent" : value[2],
        "child_order" : value[3],
        "description" : value[4],
        "gid" : value[5]} for value in MB_artist_type_data
    ]
    connection.execute(artist_type_query, values)
    transaction.commit()
    print("INSERTED artist_type data\n")


def write_area_type(transaction, connection):
    area_type_query = text("""
        INSERT INTO musicbrainz.area_type
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_area_type_data
    ]
    connection.execute(area_type_query, values)
    transaction.commit()
    print("INSERTED area_type data\n")


def write_begin_area_type(transaction, connection):
    begin_area_type_query = text("""
        INSERT INTO musicbrainz.area_type
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_begin_area_type_data
    ]
    connection.execute(begin_area_type_query, values)
    transaction.commit()
    print("INSERTED begin_area_type data\n")


def write_end_area_type(transaction, connection):
    end_area_type_query = text("""
        INSERT INTO musicbrainz.area_type
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_end_area_type_data
    ]
    connection.execute(end_area_type_query, values)
    transaction.commit()
    print("INSERTED end_area_type data\n")


def write_release_status(transaction, connection):
    release_status_query = text("""
        INSERT INTO musicbrainz.release_status
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values= [{
        "id": value[0],
        "name":  value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_release_status_data
    ]
    result = connection.execute(release_status_query, values)
    transaction.commit()
    print("INSERTED release_status data\n")


def write_release_group_primary_type(transaction, connection):
    release_group_primary_type_query = text("""
        INSERT INTO musicbrainz.release_group_primary_type
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_release_group_primary_type_data
    ]
    connection.execute(release_group_primary_type_query, values)
    transaction.commit()
    print("INSERTED release_group_primary_type data\n")


def write_medium_format(transaction, connection):
    medium_format_query = text("""
        INSERT INTO musicbrainz.medium_format
            VALUES (:id, :name, :parent, :child_order, :year, :has_discids, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "year": value[4],
        "has_discids": value[5],
        "description": value[6],
        "gid": value[7]} for value in MB_medium_format_data
    ]
    connection.execute(text("""ALTER TABLE musicbrainz.medium_format DROP CONSTRAINT IF EXISTS medium_format_fk_parent"""))
    connection.execute(medium_format_query, values)
    transaction.commit()
    print("INSERTED medium_format data\n")


def write_release_packaging(transaction, connection):
    release_packaging_query = text("""
        INSERT INTO musicbrainz.release_packaging
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_release_packaging_data
    ]
    connection.execute(release_packaging_query, values)
    transaction.commit()
    print("INSERTED release_packaging data\n")


def write_language(transaction, connection):
    language_query = text("""
        INSERT INTO musicbrainz.language
            VALUES (:iso_code_2t, :iso_code_2b, :iso_code_1, :name, :frequency, :iso_code_3)
    """)
    values = [{
        "iso_code_2t": value[0],
        "iso_code_2b": value[1],
        "iso_code_1": value[2],
        "name": value[3],
        "frequency": value[4],
        "iso_code_3": value[5]} for value in MB_language_data
    ]
    connection.execute(language_query, values)
    transaction.commit()
    print("INSERTED language data\n")


def write_script(transaction, connection):
    script_query = text("""
        INSERT INTO musicbrainz.script
            VALUES (:id, :iso_code, :iso_number, :name, :frequency)
    """)
    values = [{
        "id": value[0],
        "iso_code": value[1],
        "iso_number": value[2],
        "name": value[3],
        "frequency": value[4]} for value in MB_script_data
    ]
    connection.execute(script_query, values)
    transaction.commit()
    print("INSERTED script data\n")


def write_gender(transaction, connection):
    gender_query = text("""
        INSERT INTO musicbrainz.gender
            VALUES (:id, :name, :parent, :child_order, :description, :gid)
    """)
    values = [{
        "id": value[0],
        "name": value[1],
        "parent": value[2],
        "child_order": value[3],
        "description": value[4],
        "gid": value[5]} for value in MB_gender_data
    ]
    connection.execute(gender_query, values)
    transaction.commit()
    print("INSERTED gender data\n")


def write_area(transaction, connection):
    area_query = text("""
        INSERT INTO musicbrainz.area
            VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                    :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                    :ended, :comment)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "type": value[3],
        "edits_pending": value[4],
        "last_updated": value[5],
        "begin_date_year": value[6],
        "begin_date_month": value[7],
        "begin_date_day": value[8],
        "end_date_year": value[9],
        "end_date_month": value[10],
        "end_date_day": value[11],
        "ended": value[12],
        "comment": value[13]} for value in MB_area_data
    ]
    connection.execute(area_query, values)
    transaction.commit()
    print("INSERTED area data\n")


def write_begin_area(transaction, connection):
    begin_area_query = text("""
        INSERT INTO musicbrainz.area
            VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                    :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                    :ended, :comment)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "type": value[3],
        "edits_pending": value[4],
        "last_updated": value[5],
        "begin_date_year": value[6],
        "begin_date_month": value[7],
        "begin_date_day": value[8],
        "end_date_year": value[9],
        "end_date_month": value[10],
        "end_date_day": value[11],
        "ended": value[12],
        "comment": value[13]} for value in MB_begin_area_data
    ]
    connection.execute(begin_area_query, values)
    transaction.commit()
    print("INSERTED begin_area data\n")


def write_end_area(transaction, connection):
    end_area_query = text("""
        INSERT INTO musicbrainz.area
            VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                    :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                    :ended, :comment)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "type": value[3],
        "edits_pending": value[4],
        "last_updated": value[5],
        "begin_date_year": value[6],
        "begin_date_month": value[7],
        "begin_date_day": value[8],
        "end_date_year": value[9],
        "end_date_month": value[10],
        "end_date_day": value[11],
        "ended": value[12],
        "comment": value[13]} for value in MB_end_area_data
    ]
    connection.execute(end_area_query, values)
    transaction.commit()
    print("INSERTED end_area data\n")


def write_artist(transaction, connection):
    artist_query = text("""
      INSERT INTO musicbrainz.artist
          VALUES (:id, :gid, :name, :sort_name, :begin_date_year, :begin_date_month, :begin_date_day,
                :end_date_year, :end_date_month, :end_date_day, :type, :area, :gender, :comment, :edits_pending,
                :last_updated, :ended, :begin_area, :end_area)
          ON conflict do nothing
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "sort_name": value[3],
        "begin_date_year": value[4],
        "begin_date_month": value[5],
        "begin_date_day": value[6],
        "end_date_year": value[7],
        "end_date_month": value[8],
        "end_date_day": value[9],
        "type": value[10],
        "area": value[11],
        "gender": value[12],
        "comment": value[13],
        "edits_pending": value[14],
        "last_updated": value[15],
        "ended": value[16],
        "begin_area": value[17],
        "end_area": value[18]} for value in MB_artist_data
    ]
    connection.execute(artist_query, values)
    transaction.commit()
    print("INSERTED artist data\n")


def write_artist_credit_name(transaction, connection):
    artist_credit_name_query = text("""
        INSERT INTO musicbrainz.artist_credit_name
            VALUES (:artist_credit, :position, :artist, :name, :join_phrase)
    """)
    values = [{
        "artist_credit": value[0],
        "position": value[1],
        "artist": value[2],
        "name": value[3],
        "join_phrase": value[4]} for value in MB_artist_credit_name_data
    ]
    connection.execute(artist_credit_name_query, values)
    transaction.commit()
    print("INSERTED artist_credit_name data\n")


def write_artist_gid_redirect(transaction, connection):
    artist_gid_redirect_query = text("""
        INSERT INTO musicbrainz.artist_gid_redirect
            VALUES (:gid, :new_id, :created)
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_artist_gid_redirect_data
    ]
    connection.execute(artist_gid_redirect_query, values)
    transaction.commit()
    print("INSERTED artist_gid_redirect data\n")


def write_recording(transaction, connection):
    recording_query = text("""
        INSERT INTO musicbrainz.recording
            VALUES (:id, :gid, :name, :artist_credit, :length, :comment, :edits_pending, :last_updated, :video)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "artist_credit": value[3],
        "length": value[4],
        "comment": value[5],
        "edits_pending": value[6],
        "last_updated": value[7],
        "video": value[8]} for value in MB_recording_data
    ]
    connection.execute(recording_query, values)
    transaction.commit()
    print("INSERTED recording data\n")


def write_recording_gid_redirect(transaction, connection):
    recording_gid_redirect_query = text("""
        INSERT INTO musicbrainz.recording_gid_redirect
            VALUES (:gid, :new_id, :created)
    """)
    values = [{"gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_recording_gid_redirect_data
    ]
    connection.execute(recording_gid_redirect_query, values)
    transaction.commit()
    print("INSERTED recording_gid_redirect data\n")


def write_release_group(transaction, connection):
    release_group_query = text("""
        INSERT INTO musicbrainz.release_group
            VALUES (:id, :gid, :name, :artist_credit, :type, :comment, :edits_pending, :last_updated)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "artist_credit": value[3],
        "type": value[4],
        "comment": value[5],
        "edits_pending": value[6],
        "last_updated": value[7]} for value in MB_release_group_data
    ]
    connection.execute(release_group_query, values)
    transaction.commit()
    print("INSERTED release_group data\n")


def write_release_group_gid_redirect(transaction, connection):
    release_group_gid_redirect_query = text("""
        INSERT INTO musicbrainz.release_group_gid_redirect
            VALUES (:gid, :new_id, :created)
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_release_gid_redirect_data
    ]
    connection.execute(release_group_gid_redirect_query, values)
    transaction.commit()
    print("INSERTED release_gid_redirect data\n")


def write_release(transaction, connection):
    release_query = text("""
        INSERT INTO musicbrainz.release
            VALUES (:id, :gid, :name, :artist_credit, :release_group, :status, :packaging, :language,
                    :script, :barcode, :comment, :edits_pending, :quality, :last_updated)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "name": value[2],
        "artist_credit": value[3],
        "release_group": value[4],
        "status": value[5],
        "packaging": value[6],
        "language": value[7],
        "script": value[8],
        "barcode": value[9],
        "comment": value[10],
        "edits_pending": value[11],
        "quality": value[12],
        "last_updated": value[13]} for value in MB_release_data
    ]
    connection.execute(release_query, values)
    transaction.commit()
    print("INSERTED release data\n")


def write_release_gid_redirect(transaction, connection):
    release_gid_redirect_query = text("""
        INSERT INTO musicbrainz.release_gid_redirect
            VALUES (:gid, :new_id, :created)
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_release_gid_redirect_data
    ]
    connection.execute(release_gid_redirect_query, values)
    transaction.commit()
    print("INSERTED release_gid_redirect data\n")


def write_medium(transaction, connection):
    medium_query = text("""
        INSERT INTO musicbrainz.medium
            VALUES (:id, :release, :position, :format, :name, :edits_pending, :last_updated, :track_count)
    """)
    values = [{
        "id": value[0],
        "release": value[1],
        "position": value[2],
        "format": value[3],
        "name": value[4],
        "edits_pending": value[5],
        "last_updated": value[6],
        "track_count": value[7]} for value in MB_medium_data
    ]
    connection.execute(medium_query, values)
    transaction.commit()
    print("INSERTED medium data\n")


def write_track(transaction, connection):
    track_query = text("""
        INSERT INTO musicbrainz.track
            VALUES (:id, :gid, :recording, :medium, :position, :number, :name, :artist_credit, :length,
                    :edits_pending, :last_updated, :is_data_track)
    """)
    values = [{
        "id": value[0],
        "gid": value[1],
        "recording": value[2],
        "medium": value[3],
        "position": value[4],
        "number": value[5],
        "name": value[6],
        "artist_credit": value[7],
        "length": value[8],
        "edits_pending": value[9],
        "last_updated": value[10],
        "is_data_track": value[11]} for value in MB_track_data
    ]
    connection.execute(track_query, values)
    transaction.commit()
    print("INSERTED track data\n")




# FUNCTION TO CALL ALL INSERTS

def insert_MB_data_AB():
    with db.engine.connect() as connection:
        if MB_artist_credit_data:
            transaction = connection.begin()
            try:
                write_artist_credit(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_artist_type_data:
            transaction = connection.begin()
            try:
                write_artist_type(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_area_type_data:
            transaction = connection.begin()
            try:
                write_area_type(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_begin_area_type_data:
            transaction = connection.begin()
            try:
                write_begin_area_type(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_end_area_type_data:
            transaction = connection.begin()
            try:
                write_end_area_type(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_status_data:
            transaction = connection.begin()
            try:
                write_release_status(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_group_primary_type_data:
            transaction = connection.begin()
            try:
                write_release_group_primary_type(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_medium_format_data:
            transaction = connection.begin()
            try:
                write_medium_format(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_packaging_data:
            transaction = connection.begin()
            try:
                write_release_packaging(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_language_data:
            transaction = connection.begin()
            try:
                write_language(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_script_data:
            transaction = connection.begin()
            try:
                write_script(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_gender_data:
            transaction = connection.begin()
            try:
                write_gender(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_area_data:
            transaction = connection.begin()
            try:
                write_area(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_begin_area_data:
            transaction = connection.begin()
            try:
                write_begin_area(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_end_area_data:
            transaction = connection.begin()
            try:
                write_end_area(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_artist_data:
            transaction = connection.begin()
            try:
                write_artist(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_artist_credit_name_data:
            transaction = connection.begin()
            try:
                write_artist_credit_name(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_artist_gid_redirect_data:
            transaction = connection.begin()
            try:
                write_artist_gid_redirect(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()


        if MB_recording_data:
            transaction = connection.begin()
            try:
                write_recording(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_recording_gid_redirect_data:
            transaction = connection.begin()
            try:
                write_recording_gid_redirect(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_group_data:
            transaction = connection.begin()
            try:
                write_release_group(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_group_gid_redirect_data:
            transaction = connection.begin()
            try:
                write_release_group_gid_redirect(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_data:
            transaction = connection.begin()
            try:
                write_release(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_release_gid_redirect_data:
            transaction = connection.begin()
            try:
                write_release_gid_redirect(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_medium_data:
            transaction = connection.begin()
            try:
                write_medium(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()

        if MB_track_data:
            transaction = connection.begin()
            try:
                write_track(transaction, connection)
            except IntegrityError as e:
                print(e.message)
                transaction.rollback()


def fetch_musicbrainz_data(gids_in_AB):
    with musicbrainz_db.engine.begin() as connection:
        # track
        try:
            load_track(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # MEDIUM
        try:
            load_medium(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # release_gid_redirect
        try:
            load_release_gid_redirect(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # RELEASE
        try:
            load_release(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # ARTIST CREDIT
        try:
            load_artist_credit(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # ARTIST CREDIT NAME
        try:
            load_artist_credit_name(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # ARTIST
        try:
            load_artist(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # ARTIST TYPE
        try:
            load_artist_type(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # RECORDING
        try:
            load_recording(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # AREA
        try:
            load_area(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # BEGIN AREA
        try:
            load_begin_area(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # END AREA
        try:
            load_end_area(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # AREA TYPE
        try:
            load_area_type(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # BEGIN AREA TYPE
        try:
            load_begin_area_type(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # END AREA TYPE
        try:
            load_end_area_type(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # ARTIST GID REDIRECT
        try:
            load_artist_gid_redirect(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # GENDER
        try:
            load_gender(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # LANGUAGE
        try:
            load_language(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # MEDIUM FORMAT
        try:
            load_medium_format(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # RECORDING GID REDIRECT
        try:
            load_recording_gid_redirect(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # release_group gid redirect
        try:
            load_release_group_gid_redirect(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # release_group
        try:
            load_release_group(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # release_group_primary_type
        try:
            load_release_group_primary_type(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # release_packaging
        try:
            load_release_packaging(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # release_status
        try:
            load_release_status(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

        # script
        try:
            load_script(connection, gids_in_AB)
        except ValueError:
            print("No Data found for the recordings")

    insert_MB_data_AB()
    print("--------------------------------DONE-----------------------------------")


def start_import():
    with db.engine.begin() as connection:
        lowlevel_query = text("""SELECT gid from lowlevel""")
        gids = connection.execute(lowlevel_query)
        gids = gids.fetchall()
        gids_in_AB = [value[0] for value in gids]
        no_of_rows = len(gids_in_AB)
        start = 0
        rows_to_fetch = 10000
        for value in range(0, (no_of_rows/rows_to_fetch) + 1):
            fetch_musicbrainz_data(gids_in_AB[start : start + rows_to_fetch])
            start = start + rows_to_fetch
