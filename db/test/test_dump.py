from __future__ import absolute_import
from webserver.testing import AcousticbrainzTestCase
from db import dump
from db.dump import _TABLES

import os
import os.path
import tempfile
import shutil
import unittest


class DatabaseDumpTestCase(AcousticbrainzTestCase):

    def setUp(self):
        super(DatabaseDumpTestCase, self).setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(DatabaseDumpTestCase, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def test_dump_db(self):
        path = dump.dump_public_tables(self.temp_dir, full=True)
        self.assertTrue(os.path.isfile(path))

    def test_import_db_dump(self):
        path = dump.dump_public_tables(self.temp_dir, full=True)
        id1 = dump.list_dumps()[-1][0]
        self.reset_db()
        dump.import_db_dump(path, _TABLES)
        self.assertEqual(dump.list_dumps()[0][0], id1)
        id2 = dump._create_new_dump_record()[0]
        self.assertGreater(id2, id1)

    def test_dump_lowlevel_json(self):
        path = dump.dump_lowlevel_json(self.temp_dir, full=True)
        for f in os.listdir(path):
            self.assertTrue(os.path.isfile(os.path.join(path, f)))

    @unittest.skip
    def test_dump_highlevel_json(self):
        path = dump.dump_highlevel_json(self.temp_dir, full=True)
        self.assertTrue(os.path.isfile(path))

    def test_create_new_dump_record(self):
        id_1 = dump._create_new_dump_record()[0]
        id_2 = dump._create_new_dump_record()[0]
        self.assertTrue(id_1 < id_2)
        dump_1 = dump.get_dump_info(id_1)
        dump_2 = dump.get_dump_info(id_2)
        self.assertEqual(dump_1["dump_type"], "partial")
        self.assertEqual(dump_2["dump_type"], "partial")
        id_3 = dump._create_new_dump_record(full=True)[0]
        dump_3 = dump.get_dump_info(id_3)
        self.assertEqual(dump_3["dump_type"], "full")

    def test_get_last_dump_info(self):
        dump_id, dump_time = dump._create_new_dump_record()
        self.assertEqual(dump.list_dumps()[0][1], dump_time)

    def test_prepare_dump(self):
        self.reset_db()

        dump_id_first, start_t_first, end_t_first, full = dump.prepare_dump(full=True)
        self.assertIsNone(start_t_first)
        self.assertIsNotNone(end_t_first)
        self.assertTrue(full)

        dump_id_same, start_t_same, end_t_same, full = dump.prepare_dump(dump_id_first)
        self.assertEqual(dump_id_same, dump_id_first)
        self.assertEqual(start_t_same, start_t_first)
        self.assertEqual(end_t_same, end_t_first)

        with self.assertRaises(dump.NoNewData):
            dump.prepare_dump()

        self.load_low_level_data("0dad432b-16cc-4bf0-8961-fd31d124b01b")

        dump_id_last, start_t_last, end_t_last, full = dump.prepare_dump()
        self.assertNotEqual(dump_id_last, dump_id_first)
        self.assertNotEqual(start_t_last, start_t_first)
        self.assertNotEqual(end_t_last, end_t_first)

        self.load_low_level_data("e8afe383-1478-497e-90b1-7885c7f37f6e")

        dump_id_full, start_t_full, end_t_full, full = dump.prepare_dump(full=True)
        self.assertNotEqual(dump_id_full, dump_id_last)
        self.assertIsNone(start_t_full)
        self.assertNotEqual(end_t_full, end_t_first)
