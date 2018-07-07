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

include_tables = ['language', 'artist_credit_name', 'artist', 'artist_gid_redirect', 'area', 'area_type', 'recording_gid_redirect', \
                  'script', 'release_gid_redirect', 'recording', 'track', 'artist_credit', 'release_group_primary_type', 'release_group', \
                  'release_group_gid_redirect', 'release', 'medium', 'medium_format', 'release_status', 'release_packaging', 'gender', \
                  'artist_type']

ESCAPES = (('\\b', '\b'), ('\\f', '\f'), ('\\n', '\n'), ('\\r', '\r'),
           ('\\t', '\t'), ('\\v', '\v'), ('\\\\', '\\'))

def parse_name(table):
    if '.' in table:
        schema, table = table.split('.', 1)
        schema = 'musicbrainz'
    table = table.strip('"')
    return schema, table


def parse_data_fields(s):
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
    if s == '\\N':
        return None
    for orig, repl in ESCAPES:
        s = s.replace(orig, repl)
    return s


def read_psql_dump(fp, types):
    for line in fp:
        values = map(unescape, line.rstrip('\r\n').split('\t'))
        for i, value in enumerate(values):
            if value is not None:
                values[i] = types[i](value)
        yield values


def get_table_and_data(message):
    mess = message.split(' ')
    word = mess.index('Key') + 1
    column, data = mess[word].split('=')
    column, data = column.strip('()'), data.strip('()')
    return column, data


def insert_new_row(table, data, main_connection, main_transaction, sql, params, todo_list=None):
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
    try:
        main_connection.execute(sql, params)
        main_transaction.commit()
    except IntegrityError as e:
        main_transaction.rollback()
        table, data = get_table_and_data(e.message)
        insert_new_row(table, data, main_connection, main_transaction, sql, params)


class PacketImporter(object):

    def __init__(self, replication_seq):
        self._data = {}
        self._transactions = {}
        self._replication_seq = replication_seq

    def load_pending_data(self, fp):
        dump = read_psql_dump(fp, [int, parse_bool, parse_data_fields])
        for id, key, values in dump:
            self._data[(id, key)] = values

    def load_pending(self, fp):
        dump = read_psql_dump(fp, [int, str, str, int])
        for id, table, type, xid in dump:
            schema, table = parse_name(table)
            transaction = self._transactions.setdefault(xid, [])
            transaction.append((id, schema, table, type))

    def process(self):
        with db.engine.connect() as connection:
            stats = {}
            for xid in sorted(self._transactions.keys()):
                transaction = self._transactions[xid]
                print ' - Running transaction', xid
                for id, schema, table, type in sorted(transaction):
                    trans = connection.begin()
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
                                    print 'Deleted rows from ' + table + ' table'
                                except IntegrityError as e:
                                    trans.rollback()
                        if type == 'u':
                            if keys or values:
                                update_row(sql, params, connection, trans)
                                print 'Updated rows in ' + table + ' table'
                    print 'COMMIT; --', xid
                # print ' - Statistics:'
                # for table in sorted(stats.keys()):
                #     print '   * %-30s\t%d\t%d' % (table, stats[table]['u'], stats[table]['d'])
            print secsy


def process_tar(fileobj, expected_schema_seq, replication_seq):
    print "Processing", fileobj.name
    tar = tarfile.open(fileobj=fileobj, mode='r:bz2')
    importer = PacketImporter(replication_seq)
    for member in tar:
        if member.name == 'SCHEMA_SEQUENCE':
            schema_seq = int(tar.extractfile(member).read().strip())
            if schema_seq != expected_schema_seq:
                raise Exception("Mismatched schema sequence, %d (database) vs %d (replication packet)" % (expected_schema_seq, schema_seq))
        elif member.name == 'TIMESTAMP':
            ts = tar.extractfile(member).read().strip()
            print ' - Packet was produced at', ts
        elif member.name in ('mbdump/Pending', 'mbdump/dbmirror_pending'):
            importer.load_pending(tar.extractfile(member))
        elif member.name in ('mbdump/PendingData', 'mbdump/dbmirror_pendingdata'):
            importer.load_pending_data(tar.extractfile(member))
    importer.process()


def download_packet(base_url, token, replication_seq):
    url = base_url.rstrip("/") + "/replication-%d.tar.bz2" % replication_seq
    if token:
        url += '?token=' + token
    print "Downloading", url
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


def update_replication_sequence(replication_seq):
    with db.engine.begin() as connection:
        query = text("""
            UPDATE musicbrainz.replication_control
               SET current_replication_sequence = %s""" % (replication_seq)
        )
        connection.execute(query)


def write_replication_control(replication_seq):
    with db.engine.begin() as connection:
        query = text("""
            INSERT INTO musicbrainz.replication_control (current_replication_sequence)
                 VALUES (:replication_seq)
        """)
        connection.execute(query, {'replication_seq': replication_seq})


def main():
    base_url = current_app.config['REPLICATION_PACKETS_URL']
    if current_app.config['ACCESS_TOKEN']:
        token = current_app.config['ACCESS_TOKEN']
    else:
        token = None

    with musicbrainz_db.engine.begin() as connection:
        query = text("""
            SELECT current_schema_sequence, current_replication_sequence
              FROM replication_control
        """)
        result = connection.execute(query)
        schema_seq, mb_replication_seq = result.fetchone()
        print schema_seq, mb_replication_seq

    with db.engine.begin() as connection:
        query = text("""
            SELECT current_replication_sequence
              FROM musicbrainz.replication_control
        """)
        result = connection.execute(query)
        sequence = result.fetchone()
        ab_replication_seq = sequence[0]

    if ab_replication_seq is None or ab_replication_seq < mb_replication_seq:
        replication_seq = mb_replication_seq
        write_replication_control(replication_seq)
    else:
        replication_seq = ab_replication_seq
    while True:
        replication_seq += 1
        tmp = download_packet(base_url, token, replication_seq)
        if tmp is None:
            print 'Not found, stopping'
            break
        process_tar(tmp, schema_seq, replication_seq)
        tmp.close()
        update_replication_sequence(replication_seq)
        print 'Done applying all the replication packets till last hour'
