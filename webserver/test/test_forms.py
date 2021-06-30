from webserver.forms import DatasetEvaluationForm
from webserver.testing import AcousticbrainzTestCase


class DatasetEvaluationFormTestCase(AcousticbrainzTestCase):

    def test_preprocessing_values(self):
        # Empty preprocessing values
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=[])
        self.assertFalse(form.validate())
        self.assertTrue('preprocessing_values' in form.errors)

        # Not a valid preprocessing value
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=["foo"])
        self.assertFalse(form.validate())
        self.assertTrue("not a valid choice" in form.errors["preprocessing_values"][0])

        # Everything OK
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())

        # Empty preprocessing values, but svm_filtering is False, so not tested
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=False, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=[])
        self.assertTrue(form.validate())

    def test_gamma(self):
        # Non-integer value
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2  ,3,a,b,6",
                                     preprocessing_values=["lowlevel", "basic"])
        self.assertFalse(form.validate())
        self.assertEqual(form.errors["gamma_value"][0], "All values must be numerical")

        # More than 10 values
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3,4,5,6,7,8,9,10,11",
                                     preprocessing_values=["lowlevel", "basic"])
        self.assertFalse(form.validate())
        self.assertEqual(form.errors["gamma_value"][0], "Cannot have more than 10 elements")

        # Invalid, but svm_filtering is False
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=False, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="a,b,c", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())

        # Everything OK
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())

    def test_c(self):
        # Non-integer value
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1a,2b", gamma_value="1,2,3", preprocessing_values=["lowlevel", "basic"])
        self.assertFalse(form.validate())
        self.assertEqual(form.errors["c_value"][0], "All values must be numerical")

        # More than 10 values
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3,4,5,6,7,8,9,10,11", gamma_value="1",
                                     preprocessing_values=["lowlevel", "basic"])
        self.assertFalse(form.validate())
        self.assertEqual(form.errors["c_value"][0], "Cannot have more than 10 elements")

        # Invalid, but svm_filtering is False
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=False, filter_type="no_filtering",
                                     c_value="a,b,c", gamma_value="1,2", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())

        # Everything OK
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())

    def test_option_filtering(self):
        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=False, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())
        self.assertFalse(form.option_filtering.data)

        form = DatasetEvaluationForm(meta={'csrf': False},
                                     option_filtering=True, svm_filtering=True, filter_type="no_filtering",
                                     c_value="1,2,3", gamma_value="1,2,3", preprocessing_values=["lowlevel", "basic"])
        self.assertTrue(form.validate())
        self.assertTrue(form.option_filtering)
