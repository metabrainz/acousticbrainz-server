"""
The MIT License for apply_replication_changes script

Copyright (c) 2018 Rashi Sah
Copyright (c) 2018 Lukas Lalinsky

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from __future__ import print_function
import tarfile
import os
import re
import urllib2
import shutil
import tempfile
from flask import current_app
import db
from brainzutils import musicbrainz_db
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import db.import_mb_data
import db.data

include_tables = ['language', 'artist_credit_name', 'artist', 'artist_gid_redirect', 'area', 'area_type', 'recording_gid_redirect', \
                  'script', 'release_gid_redirect', 'recording', 'track', 'artist_credit', 'release_group_primary_type', 'release_group', \
                  'release_group_gid_redirect', 'release', 'medium', 'medium_format', 'release_status', 'release_packaging', 'gender', \
                  'artist_type']

ESCAPES = (('\\b', '\b'), ('\\f', '\f'), ('\\n', '\n'), ('\\r', '\r'),
           ('\\t', '\t'), ('\\v', '\v'), ('\\\\', '\\'))

def parse_name(table):
    """Store schema name and table name separately in different variables.

    Args:
        table: A combined schema and table name of the form - schema.table

    Returns:
        separate schema and table names.
    """
    if '.' in table:
        schema, table = table.split('.', 1)
        schema = 'musicbrainz'
    table = table.strip('"')
    return schema, table


def parse_data_fields(s):
    """Parses the data present in mbdump files to specific variables for their use.
    Removes useless quotes and other punctuations.

    Returns:
        Proper string with names of the data and corresponding values.
    """
    fields = {}
    for name, value in re.findall(r'''"([^"]+)"=('(?:''|[^'])*')? ''', s):
        if not value:
            value = None
        else:
            value = value[1:-1].replace("''", "'").replace("\\\\", "\\")
        fields[name] = value
    return fields


def parse_bool(s):
    return s == 't'


def unescape(s):
    """Remove extra escapes from the data.

    Returns:
        unescaped string.
    """
    if s == '\\N':
        return None
    for orig, repl in ESCAPES:
        s = s.replace(orig, repl)
    return s


def read_psql_dump(fp, types):
    """Read mbdump data, split the values present in rows in mbdump/dbmirror_pending
    and mbdata/dbmirror_pendingdata.

    Args:
        fp: tar file of replication packet.
        types: data types of all data of the rows.
    """
    for line in fp:
        values = map(unescape, line.rstrip('\r\n').split('\t'))
        for i, value in enumerate(values):
            if value is not None:
                values[i] = types[i](value)
        yield values


def get_table_and_data(message):
    """Get table name and data values from the IntegrityError message (if any) due to
    foreign key constraints.

    Args:
        message: SqlAlchemy integrity error message.

    Returns:
        column name and data values to be updated for a table.
    """
    mess = message.split(' ')
    word = mess.index('Key') + 1
    column, data = mess[word].split('=')
    column, data = column.strip('()'), data.strip('()')
    return column, data


def insert_new_row(table, data, main_connection, main_transaction, sql, params, todo_list=None):
    """This function insert new rows in the tables after we get any IntegrityError due to foreign
    key constraints.

    Args:
        table: name of the table in which the data is to be inserted.
        data: values to be inserted.
        main_connection: sql connection to write into the database.
        main_transaction: transaction for every write operation.
        sql: insert query.
        params: values for the query.
        todo_list: a list of tuples of type (table, data) used to insert new data
        in the respective tables.
    """
    if todo_list is None:
        todo_list = []
    table_name, columns, values = db.import_mb_data.get_data_from_musicbrainz(table, data)
    with db.engine.connect() as conn:
        trans = conn.begin()
        try:
            db.import_mb_data.insert_data_into_musicbrainz_schema(conn, trans, table_name, columns, values)
            if len(todo_list):
                todo_list.remove((table, data))
                table = todo_list[len(todo_list)-1][0]
                data = todo_list[len(todo_list)-1][1]
                insert_new_row(table, data, main_connection, main_transaction, sql, params, todo_list)
            else:
                update_row(sql, params, main_connection, main_transaction)
        except IntegrityError as e:
            trans.rollback()
            table, data = get_table_and_data(e.message)
            todo_list.append((table, data))
            insert_new_row(table, data, main_connection, main_transaction, sql, params, todo_list)


def update_row(sql, params, main_connection, main_transaction):
    """This function is a part of processing the replication packet to update
    the data present in database.

    Args:
        sql: update query.
        params: parameter values for the query.
        main_connection: sql connection to write into the database.
        main_transaction: transaction for every write operation.
    """
    try:
        main_connection.execute(sql, params)
        main_transaction.commit()
    except IntegrityError as e:
        main_transaction.rollback()
        table, data = get_table_and_data(e.message)
        insert_new_row(table, data, main_connection, main_transaction, sql, params)


class PacketImporter(object):
    """PacketImporter class to process the replication packets for proper changes
    in the database.
    """
    def __init__(self, replication_seq):
        """Initialization of the class objects.
        """
        self._data = {}
        self._transactions = {}
        self._replication_seq = replication_seq

    def load_pending_data(self, fp):
        """Load id, key and values from dbmirror_pending data files
        and stores them in data dictionary.

        Args:
            fp: tar file of replication packet.
        """
        dump = read_psql_dump(fp, [int, parse_bool, parse_data_fields])
        for id, key, values in dump:
            self._data[(id, key)] = values

    def load_pending(self, fp):
        """Load schema name, table names from dbmirror_pending file and
        maintain a transaction dictionary for the data specified in the files.

        Args:
            fp: tar file of replication packet.
        """
        dump = read_psql_dump(fp, [int, str, str, int])
        for id, table, type, xid in dump:
            schema, table = parse_name(table)
            transaction = self._transactions.setdefault(xid, [])
            transaction.append((id, schema, table, type))

    def process(self):
        """Process a replication packet and apply update and deletion
        for the data present in the database by running a acousticbrainz
        db connection.
        """
        with db.engine.connect() as connection:
            stats = {}
            for xid in sorted(self._transactions.keys()):
                transaction = self._transactions[xid]
                print ('Running transaction ' + str(xid) + '...')
                for id, schema, table, type in sorted(transaction):
                    trans = connection.begin()

                    # Applying the changes for the tables present in musicbrainz
                    # schema in acousticbrainz db
                    if schema == 'musicbrainz' and table in include_tables:
                        fulltable = '%s.%s' % (schema, table)
                        if fulltable not in stats:
                            stats[fulltable] = {'d': 0, 'u': 0}

                        if type == 'u' or type == 'd':
                            stats[fulltable][type] += 1
                        keys = self._data.get((id, True), {})
                        values = self._data.get((id, False), {})

                        params = []
                        if type == 'd':
                            sql = 'DELETE FROM %s' % (fulltable,)
                        elif type == 'u':
                            sql_values = ', '.join('%s=%%s' % i for i in values)
                            sql = 'UPDATE %s SET %s' % (fulltable, sql_values)
                            params = values.values()

                        if type == 'd' or type == 'u':
                            sql += ' WHERE ' + ' AND '.join('%s%s%%s' % (value, ' IS ' if keys[value] is None else '=') for value in keys.keys())
                            params.extend(keys.values())

                        if type == 'd':
                            if keys or values:
                                try:
                                    connection.execute(sql, params)
                                    trans.commit()
                                    print ('Deleted rows from ' + table + ' table')
                                except IntegrityError as e:
                                    trans.rollback()
                        if type == 'u':
                            if keys or values:
                                update_row(sql, params, connection, trans)
                                print ('Updated rows in ' + table + ' table')
                    else:
                        print ('Skipping changes, ' + table + ' table not found in the database')


def process_tar(fileobj, expected_schema_seq, replication_seq):
    """Processes the compressed replication packet, call the functions to load the data
    from mbdump/dbmirror_pending and mbdump.dbmirror_pendingdata files.
    Then call the 'process' function from PacketImporter class to apply the changes to
    the database.

    Args:
        fileobj: tar file of the replication packet.
        expected_schema_seq: The expected schema sequence that should be matched with the
        one listed in replication packets.
        replication_seq: The number of the replication packet.
    """
    print ("Processing", fileobj.name)
    tar = tarfile.open(fileobj=fileobj, mode='r:bz2')
    importer = PacketImporter(replication_seq)
    for member in tar:
        if member.name == 'SCHEMA_SEQUENCE':
            schema_seq = int(tar.extractfile(member).read().strip())
            if schema_seq != expected_schema_seq:
                raise Exception("Mismatched schema sequence, %d (database) vs %d (replication packet)" % (expected_schema_seq, schema_seq))
        elif member.name == 'TIMESTAMP':
            ts = tar.extractfile(member).read().strip()
            print (' - Packet was produced at', ts)
        elif member.name in ('mbdump/Pending', 'mbdump/dbmirror_pending'):
            importer.load_pending(tar.extractfile(member))
        elif member.name in ('mbdump/PendingData', 'mbdump/dbmirror_pendingdata'):
            importer.load_pending_data(tar.extractfile(member))
    importer.process()
    tar.close()


def download_packet(base_url, token, replication_seq):
    """Download the replication packet for the specified replication sequence
    and convert the packet into a tar.bz2 file.

    Args:
        base_url: The URL to download the replication packets from.
        token: An access token to allow download of the packets from MetaBrainz
        website. For more information, visit - https://metabrainz.org/api/

    Returns: tar file of the downloaded replication packet.
    """
    url = base_url.rstrip("/") + "/replication-%d.tar.bz2" % replication_seq
    if token:
        url += '?token=' + token
    print ("Downloading", url)
    try:
        data = urllib2.urlopen(url, timeout=60)
    except urllib2.HTTPError, e:
        if e.code == 404:
            return None
        raise
    tmp = tempfile.NamedTemporaryFile(suffix='.tar.bz2')
    shutil.copyfileobj(data, tmp)
    data.close()
    tmp.seek(0)
    return tmp


def main():
    """Fetch the replication sequence from the database and call the function
    to download all the replication packets from last replication sequence until
    the previous hour.
    """
    base_url = current_app.config['REPLICATION_PACKETS_URL']
    if current_app.config['ACCESS_TOKEN']:
        token = current_app.config['ACCESS_TOKEN']
    else:
        token = None

    schema_seq, mb_replication_seq = db.data.get_current_schema_and_replication_sequence()

    ab_replication_seq = db.data.get_replication_sequence_from_mb_schema()

    if ab_replication_seq is None or ab_replication_seq < mb_replication_seq:
        replication_seq = mb_replication_seq
        db.data.write_replication_control(replication_seq)
    else:
        replication_seq = ab_replication_seq

    while True:
        replication_seq += 1
        print ("Replication Sequence:", replication_seq)
        tmp = download_packet(base_url, token, replication_seq)
        if tmp is None:
            print ('Not found, stopping')
            break
        process_tar(tmp, schema_seq, replication_seq)
        tmp.close()
        db.data.update_replication_sequence(replication_seq)
        print ('Done applying all the replication packets till last hour')
