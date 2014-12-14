from acousticbrainz.testing import FlaskTestCase
from acousticbrainz.utils import _has_key


class UtilsTestCase(FlaskTestCase):

    def test_has_key(self):
        dictionary = {
            'test_1': {
                'inner_test':{
                    'secret_test_1': 'Hey there!',
                    'secret_test_2': 'Bye!',
                },
            },
            'test_2': 'Testing!',
        }

        self.assertTrue(_has_key(dictionary, ['test_1', 'inner_test']))
        self.assertTrue(_has_key(dictionary, ['test_1', 'inner_test', 'secret_test_2']))
        self.assertTrue(_has_key(dictionary, ['test_2']))

        self.assertFalse(_has_key(dictionary, ['test_3']))
        self.assertFalse(_has_key(dictionary, ['test_1', 'inner_test', 'secret_test_3']))
