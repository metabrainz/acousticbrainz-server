import db
from brainzutils import musicbrainz_db
from sqlalchemy import text
import time
import logging
from flask import current_app

BATCH_SLEEP_DURATION = 5 # number of seconds to wait between batches
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


def load_musicbrainz_schema_data(connection, table_name):
    """General function to load all the data from the specified
    musicbrainz schema table name.

    Args:
        connection: database connection to execute the query.
        table_name: Name of the table from musicbrainz schema.

    Returns:
        Specified table data fetched from the database.
    """
    query = text("""SELECT * FROM musicbrainz.{table_name}""".format(table_name=table_name))
    result = connection.execute(query, {'table_name': table_name})
    return result.fetchall()


def join_columns(columns):
    """Join the column names of the tables by a comma in between and
    a colon as prefix to pass the values in the insert query.

    Args:
        columns: A list of all the columns of any table.

    Returns:
        A string of column names separated by commas.
    """
    columns[0] = ':' + columns[0]
    return ',:'.join(columns)


def insert_data_into_musicbrainz_schema(connection, transaction, table_name, columns, values):
    """Insert data into musicbrainz schema tables whose table_name, column names and
    data values are specified.

    Args:
        connection: database connection to execute the query.
        transaction: transaction for every write operation.
        table_name: Name of the table to apply the insert query on.
        columns: Name of all the columns of the given table.
        values: Data values of the rows to insert into the tables.
    """
    trans = connection.begin()
    query = text("""
        INSERT INTO musicbrainz.{table_name} ({columns})
             VALUES ({column_values})
    """.format(table_name=table_name,
               columns=','.join(columns),
               value_str=join_columns(columns)))

    result = connection.execute(query)
    transaction.commit()


def get_data_from_musicbrainz(table_name, data, column='id'):
    """Fetch data from main MusicBrainz database for the given column name,
    data value and table name.

    Args:
        table_name: Table name whose data is to be fetched.
        data: data value whose corresponding row is fetched.
        column: Column names for the tables. Take default as 'id' if not
            specified.

    Returns:
        Table name, columns and data values fetched from the MusicBrainz
        database.
    """
    with musicbrainz_db.engine.begin() as connection:
        query = text("""
            SELECT *
              FROM :table_name
             WHERE :column = :data
        """)

        result = connection.execute(query, {'table_name': table_name,
                                            'column': column,
                                            'data': data}
        )

        values = dict(result.fetchone())
        columns = [key for key in values]
        return table_name, columns, value


def load_artist_credit(connection, MB_release_data, MB_release_group_data, MB_track_data, MB_artist_credit_name_data, artist_credit_from_recording):
    """Fetch artist_credit table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to release, release_group and track table.

    Args:
        connection: database connection to execute the query.
        MB_release_data (of type - sqlalchemy.resultproxy): data retrieved from the release table
            of the MusicBrainz database (should contain artist credit values).
        MB_release_group_data (of type - sqlalchemy.resultproxy): data retrieved from the release_group
            table of the MusicBrainz database (should contain artist credit values).
        MB_track_data (of type - sqlalchemy.resultproxy): data retrieved from the track table of the
            MusicBrainz database (should contain artist credit values).
        MB_artist_credit_name_data (of type - sqlalchemy.resultproxy): data retrieved from the artist_credit_name
            table of the MusicBrainz database (should contain artist credit values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        artist_credit data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to artist_credit column in release table
    MB_release_fk_artist_credit = list({value['artist_credit'] for value in MB_release_data})

    # Get data corresponding to artist_credit column in release_group table
    MB_release_group_fk_artist_credit = list({value['artist_credit'] for value in MB_release_group_data})

    # Get data corresponding to artist_credit column in track table
    MB_track_fk_artist_credit = list({value['artist_credit'] for value in MB_track_data})

    # Get data corresponding to artist_credit column in artist_credit_name table
    MB_artist_credit_name_fk_artist_credit = list({value['artist_credit'] for value in MB_artist_credit_name_data})

    if artist_credit_from_recording:
        filters.append("artist_credit.id in :ids")
        filter_data["ids"] = tuple(artist_credit_from_recording)

    if MB_release_data:
        filters.append("artist_credit.id in :release_data")
        filter_data["release_data"] = tuple(MB_release_fk_artist_credit)

    if MB_release_group_data:
        filters.append("artist_credit.id in :release_group_data")
        filter_data["release_group_data"] = tuple(MB_release_group_fk_artist_credit)

    if MB_track_data:
        filters.append("artist_credit.id in :track_data")
        filter_data["track_data"] = tuple(MB_track_fk_artist_credit)

    if MB_artist_credit_name_data:
        filters.append("artist_credit.id in :artist_credit_name_data")
        filter_data["artist_credit_name_data"] = tuple(MB_artist_credit_name_fk_artist_credit)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

    artist_credit_query = text("""
        SELECT DISTINCT artist_credit.id, artist_credit.name, artist_credit.artist_count,
               artist_credit.ref_count, artist_credit.created
           FROM artist_credit
             {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(artist_credit_query, filter_data)
    MB_artist_credit_data = result.fetchall()

    return MB_artist_credit_data


def load_artist_type(connection):
    """Fetch artist_type table data from MusicBrainz database for the recording MBIDs in
    AcousticBrainz database. Retrieving complete data because the rows in MusicBrainz database
    for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
        artist_type data fetched from MusicBrainz database.
    """
    artist_type_query = text("""
        SELECT *
          FROM artist_type
      ORDER BY id
    """)
    result = connection.execute(artist_type_query)
    MB_artist_type_data = result.fetchall()

    return MB_artist_type_data


def load_area_type(connection):
    """Fetch area_type table data from MusicBrainz database for the recording MBIDs in
    AcousticBrainz database. Retrieving complete data because the rows in MusicBrainz database
    for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
        area_type data fetched from MusicBrainz database.
    """
    area_type_query = text("""
        SELECT *
          FROM area_type
      ORDER BY id
    """)
    result = connection.execute(area_type_query)
    MB_area_type_data = result.fetchall()

    return MB_area_type_data


def load_begin_area_type(connection, artist_credit_from_recording):
    """Fetch area_type table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database for the begin area column
    in artist table.

    Args:
        connection: database connection to execute the query.
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        begin_area_type data fetched from MusicBrainz database.
    """
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
         WHERE artist_credit.id in :data
    """)
    result = connection.execute(begin_area_type_query, {'data': tuple(artist_credit_from_recording)})
    MB_begin_area_type_data = result.fetchall()

    return MB_begin_area_type_data


def load_end_area_type(connection, artist_credit_from_recording):
    """Fetch area_type table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database for the end area column in
    artist table.

    Args:
        connection: database connection to execute the query.
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        end_area_type data fetched from MusicBrainz database.
    """
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
         WHERE artist_credit.id in :data
    """)
    result = connection.execute(end_area_type_query, {'data': tuple(artist_credit_from_recording)})
    MB_end_area_type_data = result.fetchall()

    return MB_end_area_type_data


def load_release_status(connection):
    """Fetch release_status table data from MusicBrainz database for the recording MBID
    in AcousticBrainz database. Retrieving complete data because the rows in MusicBrainz database
    for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
        release_status data fetched from MusicBrainz database.
    """
    release_status_query = text("""
        SELECT *
          FROM release_status
      ORDER BY id
    """)
    result = connection.execute(release_status_query)
    MB_release_status_data = result.fetchall()

    return MB_release_status_data


def load_release_group_primary_type(connection):
    """Fetch release_group_primary_type table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database. Retrieving complete data because the rows
    in MusicBrainz database for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
       release_group_primary_type data fetched from MusicBrainz database.
    """
    release_status_query = text("""
        SELECT *
          FROM release_group_primary_type
      ORDER BY id
    """)
    result = connection.execute(release_status_query)
    MB_release_group_primary_type_data = result.fetchall()

    return MB_release_group_primary_type_data


def load_medium_format(connection):
    """Fetch medium_format table data from MusicBrainz database for the recording MBIDs in
    AcousticBrainz database. Retrieving complete data because the rows in
    MusicBrainz database for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
        medium_format data fetched from MusicBrainz database.
    """
    medium_format_query = text("""
        SELECT *
          FROM medium_format
      ORDER BY id
    """)
    result = connection.execute(medium_format_query)
    MB_medium_format_data = result.fetchall()

    return MB_medium_format_data


def load_release_packaging(connection):
    """Fetch release_packaging table data from MusicBrainz database for the recording MBIDs in
    AcousticBrainz database. Retrieving complete data because the rows in MusicBrainz database
    for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
        release_packaging data fetched from MusicBrainz database.
    """
    release_packaging_query = text("""
        SELECT *
          FROM release_packaging
      ORDER BY id
    """)
    result = connection.execute(release_packaging_query)
    MB_release_packaging_data = result.fetchall()

    return MB_release_packaging_data


def load_language(connection, MB_release_data, artist_credit_from_recording):
    """Fetch language table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to release table.

    Args:
        connection: database connection to execute the query.
        MB_release_data (of type - sqlalchemy.resultproxy): data retrieved from the
            release table of the MusicBrainz database (should contain language values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        language data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to language column in release table
    MB_release_fk_language = list({value['language'] for value in MB_release_data})

    if artist_credit_from_recording:
        filters.append("release.artist_credit in :ids")
        filter_data["ids"] = tuple(artist_credit_from_recording)

    if MB_release_data:
        filters.append("language.id in :data")
        filter_data["data"] = tuple(MB_release_fk_language)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )
    result = connection.execute(language_query, filter_data)
    MB_language_data = result.fetchall()

    return MB_language_data


def load_script(connection, MB_release_data, artist_credit_from_recording):
    """Fetch script table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to release table.

    Args:
        connection: database connection to execute the query.
        MB_release_data (of type - sqlalchemy.resultproxy): data retrieved from the
            release table of the MusicBrainz database (should contain script values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        script data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to language column in release table
    MB_release_fk_script = list({value['script'] for value in MB_release_data})

    if artist_credit_from_recording:
        filters.append("release.artist_credit in :ids")
        filter_data["ids"] = tuple(artist_credit_from_recording)

    if MB_release_data:
        filters.append("script.id in :data")
        filter_data["data"] = tuple(MB_release_fk_script)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

    script_query = text("""
        SELECT DISTINCT script.id,
               script.iso_code,
               script.iso_number,
               script.name,
               script.frequency
          FROM script
    INNER JOIN release
            ON release.script = script.id
            {filterstr}
    """.format(filterstr=filterstr)
    )
    result = connection.execute(script_query, filter_data)
    MB_script_data = result.fetchall()

    return MB_script_data


def load_gender(connection):
    """ Fetch gender table data from MusicBrainz database for the recording MBIDs in
    AcousticBrainz database. Retrieving complete data because the rows in MusicBrainz
    database for this table are much less in number.

    Args:
        connection: database connection to execute the query.
    Returns:
        gender data fetched from MusicBrainz database.
    """
    gender_query = text("""
        SELECT *
          FROM gender
      ORDER BY id
    """)
    result = connection.execute(gender_query)
    MB_gender_data = result.fetchall()

    return MB_gender_data


def load_area(connection, MB_artist_data, artist_credit_from_recording):
    """ Fetch area table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to artist table.

    Args:
        connection: database connection to execute the query.
        MB_artist_data (of type - sqlalchemy.resultproxy): data retrieved from the
            artist table of the MusicBrainz database (should contain area values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        area data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to area column in artist table
    MB_artist_fk_area = list({value['area'] for value in MB_artist_data})

    if artist_credit_from_recording:
        filters.append("artist_credit.id in :credit")
        filter_data["credit"] = tuple(artist_credit_from_recording)

    if MB_artist_data:
        filters.append("area.id in :data")
        filter_data["data"] = tuple(MB_artist_fk_area)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
             {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(area_query, filter_data)
    MB_area_data = result.fetchall()

    return MB_area_data


def load_begin_area(connection, MB_artist_data, artist_credit_from_recording):
    """Fetch area table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database for begin area column.

    Also fetch data corresponding to artist table.

    Args:
        connection: database connection to execute the query.
        MB_artist_data (of type - sqlalchemy.resultproxy): data retrieved from the
            artist table of the MusicBrainz database (should contain begin_area values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        begin_area data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to begin_area column in artist table
    MB_artist_fk_begin_area = list({value['begin_area'] for value in MB_artist_data})

    if artist_credit_from_recording:
        filters.append("artist_credit.id in :credit")
        filter_data["credit"] = tuple(artist_credit_from_recording)

    if MB_artist_data:
        filters.append("area.id in :data")
        filter_data["data"] = tuple(MB_artist_fk_begin_area)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(begin_area_query, filter_data)
    MB_begin_area_data = result.fetchall()

    return MB_begin_area_data


def load_end_area(connection, MB_artist_data, artist_credit_from_recording):
    """Fetch area table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database for end area column.

    Also fetch data corresponding to artist table.

    Args:
        connection: database connection to execute the query.
        MB_artist_data (of type - sqlalchemy.resultproxy): data retrieved from the
            artist table of the MusicBrainz database (should contain end_area values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        end_area data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to end_area column in artist table
    MB_artist_fk_end_area = list({value['end_area'] for value in MB_artist_data})

    if artist_credit_from_recording:
        filters.append("artist_credit.id in :ids")
        filter_data["ids"] = tuple(artist_credit_from_recording)

    if MB_artist_data:
        filters.append("area.id in :data")
        filter_data["data"] = tuple(MB_artist_fk_end_area)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )
    result = connection.execute(end_area_query, filter_data)
    MB_end_area_data = result.fetchall()

    return MB_end_area_data


def load_artist_credit_name(connection, artist_credit_from_recording):
    """Fetch artist_credit_name table data from MusicBrainz database
    for the recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        artist_credit_name data fetched from MusicBrainz database.
    """
    artist_credit_name_query = text("""
        SELECT DISTINCT artist_credit_name.artist_credit,
               artist_credit_name.position,
               artist_credit_name.artist,
               artist_credit_name.name,
               artist_credit_name.join_phrase
          FROM artist_credit_name
    INNER JOIN artist_credit
            ON artist_credit_name.artist_credit = artist_credit.id
         WHERE artist_credit.id in :data
    """)
    result = connection.execute(artist_credit_name_query, {'data': tuple(artist_credit_from_recording)})
    MB_artist_credit_name_data = result.fetchall()

    return MB_artist_credit_name_data


def load_artist(connection, MB_artist_credit_name_data, MB_artist_gid_redirect_data, artist_credit_from_recording):
    """Fetch artist table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to artist_credit_name table.

    Args:
        connection: database connection to execute the query.
        MB_artist_credit_name_data (of type - sqlalchemy.resultproxy): data retrieved from the
            artist_credit_name table of the MusicBrainz database (should contain artist values).
        MB_artist_gid_redirect_data (of type - sqlalchemy.resultproxy): data retrieved from the
            artist_gid_redirect table of the MusicBrainz database (should contain artist values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        artist data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to artist column in artist_credit_name table.
    MB_artist_credit_name_fk_artist = list({value['artist'] for value in MB_artist_credit_name_data})

    # Get data corresponding to new_id column in artist_gid_redirect table.
    MB_artist_gid_redirect_fk_artist = list({value['new_id'] for value in MB_artist_gid_redirect_data})

    if artist_credit_from_recording:
        filters.append("artist_credit.id in :credit")
        filter_data["credit"] = tuple(artist_credit_from_recording)

    if MB_artist_credit_name_data:
        filters.append("artist.id in :data")
        filter_data["data"] = tuple(MB_artist_credit_name_fk_artist)

    if MB_artist_gid_redirect_data:
        filters.append("artist.id in :redirect_data")
        filter_data["redirect_data"] = tuple(MB_artist_gid_redirect_fk_artist)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

    artist_query = text("""
        SELECT DISTINCT artist.id, artist.gid, artist.name, artist.sort_name, artist.begin_date_year,
               artist.begin_date_month, artist.begin_date_day, artist.end_date_year, artist.end_date_month,
               artist.end_date_day, artist.type, artist.area, artist.gender, artist.comment, artist.edits_pending,
               artist.last_updated, artist.ended, artist.begin_area, artist.end_area
          FROM artist
    INNER JOIN artist_credit
            ON artist_credit.id = artist.id
            {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(artist_query, filter_data)
    MB_artist_data = result.fetchall()

    return MB_artist_data


def load_artist_gid_redirect(connection, artist_credit_from_recording):
    """Fetch artist_gid_redirect table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        artist_gid_redirect data fetched from MusicBrainz database.
    """
    artist_gid_redirect_query = text("""
        SELECT DISTINCT artist_gid_redirect.gid,
               artist_gid_redirect.new_id,
               artist_gid_redirect.created
          FROM artist_gid_redirect
    INNER JOIN artist
            ON artist.id = artist_gid_redirect.new_id
    INNER JOIN artist_credit
            ON artist.id = artist_credit.id
         WHERE artist_credit.id in :data
    """)
    result = connection.execute(artist_gid_redirect_query, {'data': tuple(artist_credit_from_recording)})
    MB_artist_gid_redirect_data = result.fetchall()

    return MB_artist_gid_redirect_data


def load_recording(connection, gids_in_AB, MB_recording_gid_redirect_data):
    """Fetch recording table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        gids_in_AB: list of recordings mbids present in lowlevel table in AB database.
        MB_recording_gid_redirect_data (of type - sqlalchemy.resultproxy): data retrieved from the
            recording_gid_redirect table of the MusicBrainz database (should contain recording values).
    Returns:
        recording data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to new_id column in recording_gid_redirect table.
    MB_recording_gid_redirect_fk_recording = list({value['new_id'] for value in MB_recording_gid_redirect_data})

    if gids_in_AB:
        filters.append("recording.gid in :gids")
        filter_data["gids"] = tuple(gids_in_AB)

    if MB_recording_gid_redirect_data:
        filters.append("recording.id in :redirect_data")
        filter_data["redirect_data"] = tuple(MB_recording_gid_redirect_fk_recording)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

    recording_query = text("""
        SELECT DISTINCT recording.id, recording.gid, recording.name, recording.artist_credit,
               recording.length, recording.comment, recording.edits_pending, recording.last_updated,
               recording.video
         FROM  recording
           {filterstr}
    """.format(filterstr=filterstr)
    )
    result = connection.execute(recording_query, filter_data)
    MB_recording_data = result.fetchall()

    return MB_recording_data


def load_recording_gid_redirect(connection, gids_in_AB):
    """Fetch recording_gid_redirect table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        gids_in_AB: list of recordings mbids present in lowlevel table in AB database.
    Returns:
        recording_gid_redirect data fetched from MusicBrainz database.
    """
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
    MB_recording_gid_redirect_data = result.fetchall()

    return MB_recording_gid_redirect_data


def load_release_group(connection, MB_release_group_gid_redirect_data, MB_release_data, artist_credit_from_recording):
    """Fetch release_group table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to release_group_gid_redirect and
    release table.

    Args:
        connection: database connection to execute the query.
        MB_release_group_gid_redirect_data (of type - sqlalchemy.resultproxy): data retrieved from the
            release_group_gid_redirect table of the MusicBrainz database
            (should contain release_group values).
        MB_release_data (of type - sqlalchemy.resultproxy): data retrieved from the
            release table of the MusicBrainz database (should contain release_group values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        release_group data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to release_group column in release_group_gid_redirect table.
    MB_release_group_gid_redirect_fk_release_group = list({value['new_id'] for value in MB_release_group_gid_redirect_data})

    # Get data corresponding to release_group column in release table.
    MB_release_fk_release_group = list({value['release_group'] for value in MB_release_data})

    if artist_credit_from_recording:
        filters.append("release_group.artist_credit in :credit")
        filter_data["credit"] = tuple(artist_credit_from_recording)

    if MB_release_group_gid_redirect_data:
        filters.append("release_group.id in :redirect_data")
        filter_data["redirect_data"] = tuple(MB_release_group_gid_redirect_fk_release_group)

    if MB_release_data:
        filters.append("release_group.id in :release_data")
        filter_data["release_data"] = tuple(MB_release_fk_release_group)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(release_group_query, filter_data)
    MB_release_group_data = result.fetchall()

    return MB_release_group_data


def load_release_group_gid_redirect(connection, artist_credit_from_recording):
    """Fetch release_group_gid_redirect table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        release_group_gid_redirect data fetched from MusicBrainz database.
    """
    release_group_gid_redirect_query = text("""
        SELECT DISTINCT release_group_gid_redirect.gid,
               release_group_gid_redirect.new_id,
               release_group_gid_redirect.created
          FROM release_group_gid_redirect
    INNER JOIN release_group
            ON release_group.id = release_group_gid_redirect.new_id
         WHERE release_group.artist_credit in :data
    """)
    result = connection.execute(release_group_gid_redirect_query, {'data': tuple(artist_credit_from_recording)})
    MB_release_group_gid_redirect_data = result.fetchall()

    return MB_release_group_gid_redirect_data


def load_release(connection, MB_medium_data, MB_release_gid_redirect_data, artist_credit_from_recording):
    """Fetch release table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to medium and release_gid_redirect table.

    Args:
        connection: database connection to execute the query.
        MB_medium_data (of type - sqlalchemy.resultproxy): data retrieved from the
            medium table of the MusicBrainz database (should contain release values).
        MB_release_gid_redirect_data (of type - sqlalchemy.resultproxy): data retrieved from the
            release_gid_redirect table of the MusicBrainz database
            (should contain release values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        release data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to release column in medium table.
    MB_medium_fk_release = list({value['release'] for value in MB_medium_data})

    # Get data corresponding to new_id column in release_gid_redirect table.
    MB_release_gid_redirect_fk_release = list({value['new_id'] for value in MB_release_gid_redirect_data})

    if artist_credit_from_recording:
        filters.append("release.artist_credit in :credit")
        filter_data["credit"] = tuple(artist_credit_from_recording)

    if MB_medium_data:
        filters.append("release.id in :medium_data")
        filter_data["medium_data"] = tuple(MB_medium_fk_release)

    if MB_release_gid_redirect_data:
        filters.append("release.id in :redirect_data")
        filter_data["redirect_data"] = tuple(MB_release_gid_redirect_fk_release)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(release_query, filter_data)
    MB_release_data = result.fetchall()

    return MB_release_data


def load_release_gid_redirect(connection, artist_credit_from_recording):
    """Fetch release_gid_redirect table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        release_gid_redirect data fetched from MusicBrainz database.
    """
    release_gid_redirect_query = text("""
        SELECT DISTINCT release_gid_redirect.gid,
               release_gid_redirect.new_id,
               release_gid_redirect.created
          FROM release_gid_redirect
    INNER JOIN release
            ON release.id = release_gid_redirect.new_id
         WHERE release.artist_credit in :data
    """)
    result = connection.execute(release_gid_redirect_query, {'data': tuple(artist_credit_from_recording)})
    MB_release_gid_redirect_data = result.fetchall()

    return MB_release_gid_redirect_data


def load_medium(connection, MB_track_data, artist_credit_from_recording):
    """Fetch medium table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to track table.

    Args:
        connection: database connection to execute the query.
        MB_track_data (of type - sqlalchemy.resultproxy): data retrieved from the
            track table of the MusicBrainz database (should contain medium values).
        artist_credit_from_recording: list of artist_credit data from recording data retrieved from
            recording table of MusicBrainz database.
    Returns:
        medium data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to medium column in track table.
    MB_track_fk_medium = list({value['medium'] for value in MB_track_data})

    if artist_credit_from_recording:
        filters.append("release.artist_credit in :credit")
        filter_data["credit"] = tuple(artist_credit_from_recording)

    if MB_track_data:
        filters.append("medium.id in :data")
        filter_data["data"] = tuple(MB_track_fk_medium)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )

    result = connection.execute(medium_query, filter_data)
    MB_medium_data = result.fetchall()

    return MB_medium_data


def load_track(connection, MB_track_gid_redirect_data, id_from_recording):
    """Fetch track table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Also fetch data corresponding to track_gid_redirect table.

    Args:
        connection: database connection to execute the query.
        MB_track_gid_redirect_data (of type - sqlalchemy.resultproxy): data retrieved from the
            track_gid_redirect table of the MusicBrainz database (should contain track values).
        id_from_recording: list of recording ids from recording data fetched from MusicBrainz database.
    Returns:
        track data fetched from MusicBrainz database.
    """
    filters = []
    filter_data = {}

    # Get data corresponding to new_id column in track_gid_redirect table.
    MB_track_gid_redirect_fk_track = list({value['new_id'] for value in MB_track_gid_redirect_data})

    if id_from_recording:
        filters.append("track.recording in :ids")
        filter_data["ids"] = tuple(id_from_recording)

    if MB_track_gid_redirect_data:
        filters.append("track.id in :redirect_data")
        filter_data["redirect_data"] = tuple(MB_track_gid_redirect_fk_track)

    filterstr = " OR ".join(filters)
    if filterstr:
        filterstr = " WHERE " + filterstr

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
            {filterstr}
    """.format(filterstr=filterstr)
    )
    result = connection.execute(track_query, filter_data)
    MB_track_data = result.fetchall()

    return MB_track_data


def load_track_gid_redirect(connection, id_from_recording):
    """Fetch track_gid_redirect table data from MusicBrainz database for the
    recording MBIDs in AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        id_from_recording: list of recording ids from recording data fetched from MusicBrainz database.
    Returns:
        track_gid_redirect data fetched from MusicBrainz database.
    """
    track_gid_redirect_query = text("""
        SELECT DISTINCT track_gid_redirect.gid,
               track_gid_redirect.new_id,
               track_gid_redirect.created
          FROM track_gid_redirect
    INNER JOIN track
            ON track.id = track_gid_redirect.new_id
         WHERE track.recording in :ids
    """)
    result = connection.execute(track_gid_redirect_query, {'ids': tuple(id_from_recording)})
    MB_track_gid_redirect_data = result.fetchall()

    return MB_track_gid_redirect_data


def write_artist_credit(connection, MB_artist_credit_data):
    """Insert data into artist_credit table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_artist_credit_data: list of artist_credit data fetched from MusicBrainz database.
    """
    artist_credit_query = text("""
        INSERT INTO musicbrainz.artist_credit
             VALUES (:id, :name, :artist_count, :ref_count, :created)
                 ON CONFLICT (id) DO NOTHING
    """)
    values = [{
        "id" : value[0],
        "name" : value[1],
        "artist_count" : value[2],
        "ref_count" : value[3],
        "created" : value[4]} for value in MB_artist_credit_data
    ]
    connection.execute(artist_credit_query, values)
    logging.info('Inserted %d rows in artist credit table!' % len(MB_artist_credit_data))


def write_artist_type(connection, MB_artist_type_data):
    """Insert data in artist_type table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_artist_type_data: list of artist_type data fetched from MusicBrainz database.
    """
    artist_type_query = text("""
        INSERT INTO musicbrainz.artist_type(id, name, parent, child_order, description, gid)
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in artist type table!' % len(MB_artist_type_data))


def write_area_type(connection, MB_area_type_data):
    """Insert data in area_type table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_area_type_data: list of area_type data fetched from MusicBrainz database.
    """
    area_type_query = text("""
        INSERT INTO musicbrainz.area_type
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in area type table!' % len(MB_area_type_data))


def write_begin_area_type(connection, MB_begin_area_type_data):
    """Insert data in area_type table in musicbrainz schema in
    AcousticBrainz database for begin_area column in artist table.

    Args:
        connection: database connection to execute the query.
        MB_begin_area_type_data: list of begin_area_type data fetched from MusicBrainz database.
    """
    begin_area_type_query = text("""
        INSERT INTO musicbrainz.area_type
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (id) DO NOTHING
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
    logging.info('Inserted %d rows in area type table for begin area data!' % len(MB_begin_area_type_data))


def write_end_area_type(connection, MB_end_area_type_data):
    """Insert data in area_type table in musicbrainz schema in
    AcousticBrainz database for end area column in artist table.

    Args:
        connection: database connection to execute the query.
        MB_end_area_type_data: list of end_area_type data fetched from MusicBrainz database.
    """
    end_area_type_query = text("""
        INSERT INTO musicbrainz.area_type(id, name, parent, child_order, description, gid)
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (id) DO NOTHING
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
    logging.info('Inserted %d rows in area type table for end area data!' % len(MB_end_area_type_data))


def write_release_status(connection, MB_release_status_data):
    """Insert data in release_status table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_status_data: list of release_status data fetched from MusicBrainz database.
    """
    release_status_query = text("""
        INSERT INTO musicbrainz.release_status
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in release status table!' % len(MB_release_status_data))


def write_release_group_primary_type(connection, MB_release_group_primary_type_data):
    """Insert data in release_group_primary_type table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_group_primary_type_data: list of release_group_primary_type data fetched from MusicBrainz database.
    """
    release_group_primary_type_query = text("""
        INSERT INTO musicbrainz.release_group_primary_type
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (id) DO NOTHING
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
    logging.info('Inserted %d rows in release group primary type table!' % len(MB_release_group_primary_type_data))


def write_medium_format(connection, MB_medium_format_data):
    """Insert data in medium_format table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_medium_format_data: list of medium_format data fetched from MusicBrainz database.
    """
    medium_format_query = text("""
        INSERT INTO musicbrainz.medium_format
             VALUES (:id, :name, :parent, :child_order, :year, :has_discids, :description, :gid)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in medium format table!' % len(MB_medium_format_data))


def write_release_packaging(connection, MB_release_packaging_data):
    """Insert data in release_packaging table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_packaging_data: list of release_packaging data fetched from MusicBrainz database.
    """
    release_packaging_query = text("""
        INSERT INTO musicbrainz.release_packaging
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in release packaging table!' % len(MB_release_packaging_data))


def write_language(connection, MB_language_data):
    """Insert data in language table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_language_data: list of language data fetched from MusicBrainz database.
    """
    language_query = text("""
        INSERT INTO musicbrainz.language
             VALUES (:id, :iso_code_2t, :iso_code_2b, :iso_code_1, :name, :frequency, :iso_code_3)
                 ON CONFLICT (iso_code_2b) DO NOTHING
    """)
    values = [{
        "id": value[0],
        "iso_code_2t": value[1],
        "iso_code_2b": value[2],
        "iso_code_1": value[3],
        "name": value[4],
        "frequency": value[5],
        "iso_code_3": value[6]} for value in MB_language_data
    ]
    connection.execute(language_query, values)
    logging.info('Inserted %d rows in language table!' % len(MB_language_data))


def write_script(connection, MB_script_data):
    """Insert data in script table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_script_data: list of script data fetched from MusicBrainz database.
    """
    script_query = text("""
        INSERT INTO musicbrainz.script
             VALUES (:id, :iso_code, :iso_number, :name, :frequency)
                 ON CONFLICT (iso_code) DO NOTHING
    """)
    values = [{
        "id": value[0],
        "iso_code": value[1],
        "iso_number": value[2],
        "name": value[3],
        "frequency": value[4]} for value in MB_script_data
    ]
    connection.execute(script_query, values)
    logging.info('Inserted %d rows in script table!' % len(MB_script_data))


def write_gender(connection, MB_gender_data):
    """Insert data in gender table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_gender_data: list of gender data fetched from MusicBrainz database.
    """
    gender_query = text("""
        INSERT INTO musicbrainz.gender
             VALUES (:id, :name, :parent, :child_order, :description, :gid)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in gender table!' % len(MB_gender_data))


def write_area(connection, MB_area_data):
    """Insert data in area table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_area_data: list of area data fetched from MusicBrainz database.
    """
    area_query = text("""
        INSERT INTO musicbrainz.area
             VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                     :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                     :ended, :comment)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in area table!' % len(MB_area_data))


def write_begin_area(connection, MB_begin_area_data):
    """Insert data in area table in musicbrainz schema in
    AcousticBrainz database for begin_area column in artist
    table.

    Args:
        connection: database connection to execute the query.
        MB_begin_area_data: list of begin_area data fetched from MusicBrainz database.
    """
    begin_area_query = text("""
        INSERT INTO musicbrainz.area
             VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                     :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                     :ended, :comment)
                 ON CONFLICT (id) DO NOTHING
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
    logging.info('Inserted %d rows in area table for begin area data!' % len(MB_begin_area_data))

def write_end_area(connection, MB_end_area_data):
    """Insert data in area table in musicbrainz schema in
    AcousticBrainz database for end_area column in artist
    table.

    Args:
        connection: database connection to execute the query.
        MB_end_area_data: list of end_area data fetched from MusicBrainz database.
    """
    end_area_query = text("""
        INSERT INTO musicbrainz.area
             VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                     :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                     :ended, :comment)
                 ON CONFLICT (id) DO NOTHING
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
    logging.info('Inserted %d rows in area table for end area data!' % len(MB_end_area_data))


def write_artist(connection, MB_artist_data):
    """Insert data in artist table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_artist_data: list of artist data fetched from MusicBrainz database.
    """
    artist_query = text("""
      INSERT INTO musicbrainz.artist
           VALUES (:id, :gid, :name, :sort_name, :begin_date_year, :begin_date_month, :begin_date_day,
                   :end_date_year, :end_date_month, :end_date_day, :type, :area, :gender, :comment, :edits_pending,
                   :last_updated, :ended, :begin_area, :end_area)
               ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in artist table!' % len(MB_artist_data))


def write_artist_credit_name(connection, MB_artist_credit_name_data):
    """Insert data in artist_credit_name table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_artist_credit_name_data: list of artist_credit_name data fetched from MusicBrainz database.
    """
    artist_credit_name_query = text("""
        INSERT INTO musicbrainz.artist_credit_name
             VALUES (:artist_credit, :position, :artist, :name, :join_phrase)
                 ON CONFLICT (artist_credit, position) DO NOTHING
    """)
    values = [{
        "artist_credit": value[0],
        "position": value[1],
        "artist": value[2],
        "name": value[3],
        "join_phrase": value[4]} for value in MB_artist_credit_name_data
    ]
    connection.execute(artist_credit_name_query, values)
    logging.info('Inserted %d rows in artist credit name table!' % len(MB_artist_credit_name_data))


def write_artist_gid_redirect(connection, MB_artist_gid_redirect_data):
    """Insert data in artist_gid_redirect table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_artist_gid_redirect_data: list of artist_gid_redirect data fetched from MusicBrainz database.
    """
    artist_gid_redirect_query = text("""
        INSERT INTO musicbrainz.artist_gid_redirect
             VALUES (:gid, :new_id, :created)
                 ON CONFLICT (gid) DO NOTHING
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_artist_gid_redirect_data
    ]
    connection.execute(artist_gid_redirect_query, values)
    logging.info('Inserted %d rows in artist gid redirect table!' % len(MB_artist_gid_redirect_data))


def write_recording(connection, MB_recording_data):
    """Insert data in recording table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_recording_data: list of recording data fetched from MusicBrainz database.
    """
    recording_query = text("""
        INSERT INTO musicbrainz.recording
             VALUES (:id, :gid, :name, :artist_credit, :length, :comment, :edits_pending, :last_updated, :video)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in recording table!' % len(MB_recording_data))


def write_recording_gid_redirect(connection, MB_recording_gid_redirect_data):
    """Insert data in recording_gid_redirect table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_recording_gid_redirect_data: list of recording_gid_redirect data fetched from MusicBrainz database.
    """
    recording_gid_redirect_query = text("""
        INSERT INTO musicbrainz.recording_gid_redirect
             VALUES (:gid, :new_id, :created)
                 ON CONFLICT (gid) DO NOTHING
    """)
    values = [{"gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_recording_gid_redirect_data
    ]
    connection.execute(recording_gid_redirect_query, values)
    logging.info('Inserted %d rows in recording gid redirect table!' % len(MB_recording_gid_redirect_data))


def write_release_group(connection, MB_release_group_data):
    """Insert data in release_group table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_group_data: list of release_group data fetched from MusicBrainz database.
    """
    release_group_query = text("""
        INSERT INTO musicbrainz.release_group
             VALUES (:id, :gid, :name, :artist_credit, :type, :comment, :edits_pending, :last_updated)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in release group table!' % len(MB_release_group_data))


def write_release_group_gid_redirect(connection, MB_release_gid_redirect_data):
    """Insert data in release_group_gid_redirect table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_group_gid_redirect_data: list of release_group_gid_redirect data fetched from MusicBrainz database.
    """
    release_group_gid_redirect_query = text("""
        INSERT INTO musicbrainz.release_group_gid_redirect
             VALUES (:gid, :new_id, :created)
                 ON CONFLICT (gid) DO NOTHING
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_release_gid_redirect_data
    ]
    connection.execute(release_group_gid_redirect_query, values)
    logging.info('Inserted %d rows in release gid redirect table!' % len(MB_release_gid_redirect_data))


def write_release(connection, MB_release_data):
    """Insert data in release table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_data: list of release data fetched from MusicBrainz database.
    """
    release_query = text("""
        INSERT INTO musicbrainz.release
             VALUES (:id, :gid, :name, :artist_credit, :release_group, :status, :packaging, :language,
                     :script, :barcode, :comment, :edits_pending, :quality, :last_updated)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in release table!' % len(MB_release_data))


def write_release_gid_redirect(connection, MB_release_gid_redirect_data):
    """Insert data in release_gid_redirect table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_release_gid_redirect_data: list of release_gid_redirect data fetched from MusicBrainz database.
    """
    release_gid_redirect_query = text("""
        INSERT INTO musicbrainz.release_gid_redirect
             VALUES (:gid, :new_id, :created)
                 ON CONFLICT (gid) DO NOTHING
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_release_gid_redirect_data
    ]
    connection.execute(release_gid_redirect_query, values)
    logging.info('Inserted %d rows in release gid redirect table!' % len(MB_release_gid_redirect_data))


def write_medium(connection, MB_medium_data):
    """Insert data in medium table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_medium_data: list of medium data fetched from MusicBrainz database.
    """
    medium_query = text("""
        INSERT INTO musicbrainz.medium
             VALUES (:id, :release, :position, :format, :name, :edits_pending, :last_updated, :track_count)
                 ON CONFLICT (id) DO NOTHING
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
    logging.info('Inserted %d rows in medium table!' % len(MB_medium_data))


def write_track(connection, MB_track_data):
    """Insert data in track table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_track_data: list of track data fetched from MusicBrainz database.
    """
    track_query = text("""
        INSERT INTO musicbrainz.track
             VALUES (:id, :gid, :recording, :medium, :position, :number, :name, :artist_credit, :length,
                     :edits_pending, :last_updated, :is_data_track)
                 ON CONFLICT (gid) DO NOTHING
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
    logging.info('Inserted %d rows in track table!' % len(MB_track_data))


def write_track_gid_redirect(connection, MB_track_gid_redirect_data):
    """Insert data in track_gid_redirect table in musicbrainz schema in
    AcousticBrainz database.

    Args:
        connection: database connection to execute the query.
        MB_track_gid_redirect_data: list of track_gid_redirect data fetched from MusicBrainz database.
    """
    track_gid_redirect_query = text("""
        INSERT INTO musicbrainz.track_gid_redirect
             VALUES (:gid, :new_id, :created)
                 ON CONFLICT (gid) DO NOTHING
    """)
    values = [{
        "gid": value[0],
        "new_id": value[1],
        "created": value[2]} for value in MB_track_gid_redirect_data
    ]
    connection.execute(track_gid_redirect_query, values)
    logging.info('Inserted %d rows in track gid redirect table!' % len(MB_track_gid_redirect_data))


def fetch_and_insert_musicbrainz_data(gids_in_AB):
    # Get MusicBrainz data
    logging.info('Getting %d recordings data at a time...\n' % (len(gids_in_AB)))
    with musicbrainz_db.engine.begin() as connection:
        # recording_gid_redirect
        try:
            logging.info('Getting recording gid redirect data...')
            MB_recording_gid_redirect_data = load_recording_gid_redirect(connection, gids_in_AB)
        except ValueError:
            logging.info("No Data found from recording gid redirect table for the recordings")

        # recording
        try:
            logging.info('Getting recording data...')
            MB_recording_data = load_recording(connection, gids_in_AB, MB_recording_gid_redirect_data)
            artist_credit_from_recording = [value[3] for value in MB_recording_data]
            id_from_recording = [value[0] for value in MB_recording_data]
        except ValueError:
            logging.info("No Data found from recording table for the recordings")

        # track_gid_redirect
        try:
            logging.info('Getting track gid redirect data...')
            MB_track_gid_redirect_data = load_track_gid_redirect(connection, id_from_recording)
        except ValueError:
            logging.info("No Data found from track gid redirect table for the recordings")

        # track
        try:
            logging.info('Getting track data...')
            MB_track_data = load_track(connection, MB_track_gid_redirect_data, id_from_recording)
        except ValueError:
            logging.info("No Data found from track table for the recordings")

        # medium
        try:
            logging.info('Getting medium data...')
            MB_medium_data = load_medium(connection, MB_track_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from medium table for the recordings")

        # release_gid_redirect
        try:
            logging.info('Getting release gid redirect data...')
            MB_release_gid_redirect_data = load_release_gid_redirect(connection, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from release gid redirect table for the recordings")

        # release
        try:
            logging.info('Getting release data...')
            MB_release_data = load_release(connection, MB_medium_data, MB_release_gid_redirect_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from release table for the recordings")

        # artist_credit_name
        try:
            logging.info('Getting artist credit name data...')
            MB_artist_credit_name_data = load_artist_credit_name(connection, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from artist credit name table for the recordings")

        # artist_gid_redirect
        try:
            logging.info('Getting artist gid redirect data...')
            MB_artist_gid_redirect_data = load_artist_gid_redirect(connection, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from artist gid redirect table for the recordings")

        # artist
        try:
            logging.info('Getting artist data...')
            MB_artist_data = load_artist(connection, MB_artist_credit_name_data, MB_artist_gid_redirect_data, artist_credit_from_recording)
            artist_type_from_artist = [value[10] for value in MB_artist_data]
        except ValueError:
            logging.info("No Data found from artist table for the recordings")

        # artist_type
        try:
            logging.info('Getting artist type data...')
            MB_artist_type_data = load_artist_type(connection)
        except ValueError:
            logging.info("No Data found from artist type table for the recordings")

        # area
        try:
            logging.info('Getting area data...')
            MB_area_data = load_area(connection, MB_artist_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from area table for the recordings")

        # begin_area
        try:
            logging.info('Getting begin area data...')
            MB_begin_area_data = load_begin_area(connection, MB_artist_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from area table for the recordings")

        # end_area
        try:
            logging.info('Getting end area data...')
            MB_end_area_data = load_end_area(connection, MB_artist_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from area table for the recordings")

        # area_type
        try:
            logging.info('Getting area type data...')
            MB_area_type_data = load_area_type(connection)
        except ValueError:
            logging.info("No Data found from area type table for the recordings")

        # begin_area_type
        try:
            logging.info('Getting begin area type data...')
            MB_begin_area_type_data = load_begin_area_type(connection, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from area type table for the recordings")

        # end_area_type
        try:
            logging.info('Getting end area data...')
            MB_end_area_type_data = load_end_area_type(connection, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from area type table for the recordings")

        # gender
        try:
            logging.info('Getting gender data...')
            MB_gender_data = load_gender(connection)
        except ValueError:
            logging.info("No Data found from gender table for the recordings")

        # language
        try:
            logging.info('Getting language data...')
            MB_language_data = load_language(connection, MB_release_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from language table for the recordings")

        # medium_format
        try:
            logging.info('Getting medium format data...')
            MB_medium_format_data = load_medium_format(connection)
        except ValueError:
            logging.info("No Data found from medium format table for the recordings")

        # release_group gid redirect
        try:
            logging.info('Getting release group gid redirect data...')
            MB_release_group_gid_redirect_data = load_release_group_gid_redirect(connection, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from release group gid redirect table for the recordings")

        # release_group
        try:
            logging.info('Getting release group data...')
            MB_release_group_data = load_release_group(connection, MB_release_group_gid_redirect_data, MB_release_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from release group table for the recordings")

        # artist_credit
        try:
            logging.info('Getting artist credit data...')
            MB_artist_credit_data = load_artist_credit(connection, MB_release_data, MB_release_group_data, MB_track_data, MB_artist_credit_name_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from artist credit table for the recordings")

        # release_group_primary_type
        try:
            logging.info('Getting release group primary type data...')
            MB_release_group_primary_type_data = load_release_group_primary_type(connection)
        except ValueError:
            logging.info("No Data found from release group primary type table for the recordings")

        # release_packaging
        try:
            logging.info('Getting release packaging data...')
            MB_release_packaging_data = load_release_packaging(connection)
        except ValueError:
            logging.info("No Data found from release packaging table for the recordings")

        # release_status
        try:
            logging.info('Getting release status data...')
            MB_release_status_data = load_release_status(connection)
        except ValueError:
            logging.info("No Data found from release status table for the recordings")

        # script
        try:
            logging.info('Getting script data...\n')
            MB_script_data = load_script(connection, MB_release_data, artist_credit_from_recording)
        except ValueError:
            logging.info("No Data found from script table for the recordings")

        # Write MusicBrainz data into AcousticBrainz database
        logging.info('Inserting %d recordings data at a time...\n' % (len(gids_in_AB)))
        with db.engine.begin() as connection:
            if MB_artist_credit_data:
                write_artist_credit(connection, MB_artist_credit_data)

            if MB_artist_type_data:
                write_artist_type(connection, MB_artist_type_data)

            if MB_area_type_data:
                write_area_type(connection, MB_area_type_data)

            if MB_begin_area_type_data:
                write_begin_area_type(connection, MB_begin_area_type_data)

            if MB_end_area_type_data:
                write_end_area_type(connection, MB_end_area_type_data)

            if MB_release_status_data:
                write_release_status(connection, MB_release_status_data)

            if MB_release_group_primary_type_data:
                write_release_group_primary_type(connection, MB_release_group_primary_type_data)

            if MB_medium_format_data:
                write_medium_format(connection, MB_medium_format_data)

            if MB_release_packaging_data:
                write_release_packaging(connection, MB_release_packaging_data)

            if MB_language_data:
                write_language(connection, MB_language_data)

            if MB_script_data:
                write_script(connection, MB_script_data)

            if MB_gender_data:
                write_gender(connection, MB_gender_data)

            if MB_area_data:
                write_area(connection, MB_area_data)

            if MB_begin_area_data:
                write_begin_area(connection, MB_begin_area_data)

            if MB_end_area_data:
                write_end_area(connection, MB_end_area_data)

            if MB_artist_data:
                write_artist(connection, MB_artist_data)

            if MB_artist_credit_name_data:
                write_artist_credit_name(connection, MB_artist_credit_name_data)

            if MB_artist_gid_redirect_data:
                write_artist_gid_redirect(connection, MB_artist_gid_redirect_data)

            if MB_recording_data:
                write_recording(connection, MB_recording_data)

            if MB_recording_gid_redirect_data:
                write_recording_gid_redirect(connection, MB_recording_gid_redirect_data)

            if MB_release_group_data:
                write_release_group(connection, MB_release_group_data)

            if MB_release_group_gid_redirect_data:
                write_release_group_gid_redirect(connection, MB_release_group_gid_redirect_data)

            if MB_release_data:
                write_release(connection, MB_release_data)

            if MB_release_gid_redirect_data:
                write_release_gid_redirect(connection, MB_release_gid_redirect_data)

            if MB_medium_data:
                write_medium(connection, MB_medium_data)

            if MB_track_data:
                write_track(connection, MB_track_data)

            if MB_track_gid_redirect_data:
                write_track_gid_redirect(connection, MB_track_gid_redirect_data)


def start_import():
    with db.engine.begin() as connection:
        offset = 0
        rows_to_fetch = current_app.config['RECORDINGS_FETCHED_PER_BATCH']
        start_time = time.time()
        while True:
            lowlevel_query = text("""SELECT gid
                                       FROM lowlevel
                                       ORDER BY id
                                       OFFSET :offset
                                       LIMIT :rows_to_fetch
                            """)
            gids = connection.execute(lowlevel_query, {"offset": offset, "rows_to_fetch": rows_to_fetch})
            gids = gids.fetchall()
            gids_in_AB = [value[0] for value in gids]
            offset = offset + rows_to_fetch

            if gids_in_AB:
                fetch_and_insert_musicbrainz_data(gids_in_AB)
                batch_sleep = current_app.config['BATCH_SLEEP_DURATION']
                logging.info("Sleeping %s seconds before starting next batch's import." % batch_sleep)
                time.sleep(batch_sleep)
            else:
                break
        logging.info('Done!')
        total_time_taken = time.time() - start_time
        logging.info('Data imported and inserted in %.2f seconds.' %  total_time_taken)
