from acousticbrainz.testing import FlaskTestCase
from acousticbrainz.data import dump
import os.path
import tempfile
import shutil


class DataDumpTestCase(FlaskTestCase):

    def setUp(self):
        super(DataDumpTestCase, self).setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(DataDumpTestCase, self).setUp()
        shutil.rmtree(self.temp_dir)

    def test_dump_db(self):
        path = dump.dump_db(self.temp_dir)
        self.assertTrue(os.path.isfile(path))

    def test_import_db_dump(self):
        path = dump.dump_db(self.temp_dir)
        dump.import_db_dump(path)

    def test_dump_lowlevel_json(self):
        path = dump.dump_lowlevel_json(self.temp_dir)
        self.assertTrue(os.path.isfile(path))

    def test_dump_highlevel_json(self):
        path = dump.dump_highlevel_json(self.temp_dir)
        self.assertTrue(os.path.isfile(path))

    def test_create_new_inc_dump_record(self):
        id_1 = dump._create_new_inc_dump_record()[0]
        id_2 = dump._create_new_inc_dump_record()[0]
        self.assertTrue(id_1 < id_2)

    def test_get_last_inc_dump_info(self):
        self.assertIsNone(dump.list_incremental_dumps())

        dump_id, dump_time = dump._create_new_inc_dump_record()
        self.assertEqual(dump.list_incremental_dumps()[0][1], dump_time)

    def test_prepare_incremental_dump(self):
        dump_id_first, start_t_first, end_t_first = dump._prepare_incremental_dump()
        self.assertIsNone(start_t_first)
        self.assertIsNotNone(end_t_first)

        dump_id_same, start_t_same, end_t_same = dump._prepare_incremental_dump(dump_id_first)
        self.assertEqual(dump_id_same, dump_id_first)
        self.assertEqual(start_t_same, start_t_first)
        self.assertEqual(end_t_same, end_t_first)

        dump_id_second, start_t_second, end_t_second = dump._prepare_incremental_dump()
        self.assertNotEqual(dump_id_second, dump_id_first)
        self.assertEqual(start_t_second, end_t_first)
        self.assertIsNotNone(end_t_second)
