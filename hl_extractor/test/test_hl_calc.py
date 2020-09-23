import os
import shutil
import subprocess
import tempfile
import unittest

import mock
import yaml

from hl_extractor import hl_calc


class HlCalcTest(unittest.TestCase):
    maxDiff = None

    def test_process_lowlevel_data_no_items(self):
        # Pass in an empty list of lowlevel items
        with self.assertRaises(ValueError):
            hl_calc.process_lowlevel_data([], None)

    def test_process_lowlevel_data_too_many(self):
        # Pass in too many lowlevel items to be processed
        old_max_items = hl_calc.MAX_ITEMS_PER_PROCESS
        hl_calc.MAX_ITEMS_PER_PROCESS = 1
        with self.assertRaises(ValueError):
            hl_calc.process_lowlevel_data([(1, 'mbid', '{data}'), (2, 'mbid', '{data2}')], None)
        hl_calc.MAX_ITEMS_PER_PROCESS = old_max_items

    @mock.patch("__builtin__.open", new_callable=mock.mock_open, read_data='{"data": 1}')
    @mock.patch("tempfile.mkdtemp")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.rmtree")
    def test_process_lowlevel_data_readwrite_failure(self, mock_rmtree, mock_check_call, mock_mkdtemp, mock_open):
        # Some lowlevel files fail to write lowlevel to or read highleve from the temp directory
        mock_mkdtemp.return_value = "/tmp/hl"
        mock_open.side_effect = (IOError,  # write lowlevel 1
                                 IOError)  # write lowlevel 2

        with self.assertRaises(hl_calc.HighLevelExtractorError) as e:
            hl_calc.process_lowlevel_data([(1, 'mbid1', '{data}'), (2, 'mbid2', '{data2}')], None)
        self.assertEqual(str(e), "Unable to write any lowlevel files to temporary directory")

    @mock.patch("__builtin__.open", new_callable=mock.mock_open, read_data='{"data": 1}')
    @mock.patch("tempfile.mkdtemp")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.rmtree")
    def test_process_lowlevel_data_readwrite_failure(self, mock_rmtree, mock_check_call, mock_mkdtemp, mock_open):
        # Some lowlevel files fail to write lowlevel to or read highleve from the temp directory
        mock_mkdtemp.return_value = "/tmp/hl"
        mock_open.side_effect = (mock_open.return_value,  # write lowlevel 1
                                 IOError,  # write lowlevel 2
                                 mock_open(os.devnull, 'w'),  # /dev/null for check_call
                                 mock_open.return_value,  # read highlevel 1
                                 IOError)  # read highlevel 2

        results = hl_calc.process_lowlevel_data([(1, 'mbid1', '{data}'), (2, 'mbid2', '{data2}')], None)

        assert len(results) == 2
        assert results[0] == (1, 'mbid1', {"data": 1})
        assert results[1] == (2, 'mbid2', {})

        # Even though 2 items were returned, the highlevel extractor was only called with 1 file because the second
        # file failed to be written
        mock_check_call.assert_called_with(
            ['/usr/local/bin/essentia_streaming_extractor_music_svm', '/tmp/hl/1-input.json', '/tmp/hl/1-output.json',
             '/code/hl_extractor/profile.conf'], stderr=mock.ANY, stdout=mock.ANY)

    @mock.patch("__builtin__.open", new_callable=mock.mock_open, read_data="{}")
    @mock.patch("tempfile.mkdtemp")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.rmtree")
    def test_process_lowlevel_data_exec_failure(self, mock_rmtree, mock_check_call, mock_mkdtemp, mock_open):
        # The binary fails to execute
        mock_mkdtemp.return_value = "/tmp/hl"
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'hl_extractor')

        with self.assertRaises(hl_calc.HighLevelExtractorError):
            hl_calc.process_lowlevel_data([(1, 'mbid', '{data}')], None)

    @mock.patch("__builtin__.open", new_callable=mock.mock_open, read_data="{}")
    @mock.patch("tempfile.mkdtemp")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.rmtree")
    def test_process_lowlevel_data_success(self, mock_rmtree, mock_check_call, mock_mkdtemp, mock_open):
        mock_mkdtemp.return_value = "/tmp/hl"

        hl_calc.process_lowlevel_data([(1, 'mbid', '{data}'), (2, 'mbid', '{data2}')], None)

        mock_open.assert_has_calls([mock.call('/tmp/hl/1-input.json', 'w'),
                                    mock.call('/tmp/hl/2-input.json', 'w'),
                                    mock.call('/tmp/hl/1-output.json', 'r'),
                                    mock.call('/tmp/hl/2-output.json', 'r')], any_order=True)

        mock_check_call.assert_called_with(
            ['/usr/local/bin/essentia_streaming_extractor_music_svm', '/tmp/hl/1-input.json', '/tmp/hl/1-output.json',
             '/tmp/hl/2-input.json', '/tmp/hl/2-output.json', '/code/hl_extractor/profile.conf'], stderr=mock.ANY,
            stdout=mock.ANY)
        mock_rmtree.assert_called_with("/tmp/hl", ignore_errors=True)

    def test_create_profile(self):
        # TODO: Use `with tempfile.TemporaryDirectory` in Python 3
        dirname = tempfile.mkdtemp()
        inputname = os.path.join(dirname, "input.yaml")
        outputname = os.path.join(dirname, "output.yaml")
        source = """
indent: 0
highlevel:
   compute: 1.
   svm_models: [/data/svm_models/danceability.history,
                /data/svm_models/gender.history
               ]
mergeValues:
    metadata:
        version:
            highlevel:
                essentia_build_sha:
                models_essentia_git_sha: v2.1
        """.strip()
        with open(inputname, "w") as fp:
            fp.write(source)
        hl_calc.create_profile(inputname, outputname, 'this_value_to_interpolate')

        expected = {'indent': 0, 'mergeValues': {
                                     'metadata': {'version': {
                                                  'highlevel': {'essentia_build_sha': 'this_value_to_interpolate',
                                                                'models_essentia_git_sha': 'v2.1'}}}},
                    'highlevel': {
                        'svm_models': ['/data/svm_models/danceability.history', '/data/svm_models/gender.history'],
                        'compute': 1.0}}

        with open(outputname, "r") as fp:
            conf = yaml.safe_load(fp)
            self.assertEqual(conf, expected)

        shutil.rmtree(dirname)

    def test_get_build_sha1(self):
        data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_data")
        data_file = os.path.join(data_dir, "known_file")
        result_sha1 = hl_calc.get_build_sha1(data_file)
        self.assertEqual(result_sha1, "018507c3c54e655320feee0a87e7b56447a45258")

        with self.assertRaises(hl_calc.HighLevelConfigurationError):
            data_file = os.path.join(data_dir, "unknown_file")
            hl_calc.get_build_sha1(data_file)
