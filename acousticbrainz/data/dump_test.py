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
