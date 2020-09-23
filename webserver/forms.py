from flask import current_app
from wtforms import BooleanField, SelectField, StringField, TextAreaField, \
    SelectMultipleField, FieldList, FormField, widgets, ValidationError
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from db import dataset_eval

DATASET_EVAL_NO_FILTER = "no_filtering"
DATASET_EVAL_LOCAL = "local"
DATASET_EVAL_REMOTE = "remote"

DATASET_PENDING = "pending"
DATASET_RUNNING = "running"
DATASET_DONE = "done"
DATASET_ALL = "all"

DATASET_C_VALUE = ", ".join([str(i) for i in dataset_eval.DEFAULT_PARAMETER_C])
DATASET_GAMMA_VALUE = ", ".join([str(i) for i in dataset_eval.DEFAULT_PARAMETER_GAMMA])
# MultiCheckboxField take multiple field values
PREPROCESSING_VALUES = [(val, val) for val in dataset_eval.DEFAULT_PARAMETER_PREPROCESSING]

# Maximum number of C and gamma values
MAX_NUMBER_PARAMETERS = 10


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class DatasetCSVImportForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired("Dataset name is required")])
    description = TextAreaField("Description")
    file = FileField("CSV file", validators=[
        FileRequired(),
        FileAllowed(["csv"], "Dataset needs to be in CSV format"),
    ])
    public = BooleanField('Make this dataset public')


class DatasetEvaluationForm(FlaskForm):

    option_filtering = BooleanField("Use advanced filtering options",
                                    render_kw={"data-toggle": "collapse",
                                               "data-target": "#collapseFilterOptions"})

    filter_type = SelectField("Filtering", choices=[
        (DATASET_EVAL_NO_FILTER, "Don't filter"),
        (dataset_eval.FILTER_ARTIST, "By Artist"),
    ], validate_choice=False)
    normalize = BooleanField("Normalize classes")
    evaluation_location = SelectField("Evaluation location", choices=[
        (DATASET_EVAL_LOCAL, "Evaluate on acousticbrainz.org"),
        (DATASET_EVAL_REMOTE, "Evaluate on your own machine")],
                                      default=DATASET_EVAL_LOCAL,
                                      validate_choice=False)

    svm_filtering = BooleanField("Use advanced SVM options",
                                 render_kw={"data-toggle": "collapse",
                                            "data-target": "#collapseSvmOptions"})

    # C parameter to SVM
    c_value = StringField('C Values', default=DATASET_C_VALUE,
                          render_kw={"data-default": DATASET_C_VALUE})

    # Gamma parameter to SVM
    gamma_value = StringField('Gamma Values', default=DATASET_GAMMA_VALUE,
                              render_kw={"data-default": DATASET_GAMMA_VALUE})

    preprocessing_values = MultiCheckboxField('Preprocessing Values', choices=PREPROCESSING_VALUES,
                                              default=[p for p, _ in PREPROCESSING_VALUES],
                                              render_kw={"class": "list-unstyled"})

    def validate_filter_type(self, field):
        if current_app.config['FEATURE_EVAL_FILTERING']:
            field.validate_choice = True
            field.pre_validate(self)

    def validate_preprocessing_values(self, field):
        # If we don't have SVM options enabled, don't validate the field
        if not self.svm_filtering.data:
            return
        if not field.data:
            raise ValidationError("Must select at least one preprocessing value")

    def validate_gamma_value(self, field):
        # If we don't have SVM options enabled, don't validate the field
        if not self.svm_filtering.data:
            return
        try:
            data = [int(value) for value in field.data.split(',')]
        except ValueError:
            raise ValidationError("All values must be numerical")
        if len(data) > MAX_NUMBER_PARAMETERS:
            raise ValidationError("Cannot have more than {} elements".format(MAX_NUMBER_PARAMETERS))

    def validate_c_value(self, field):
        # If we don't have SVM options enabled, don't validate the field
        if not self.svm_filtering.data:
            return
        try:
            data = [int(value) for value in field.data.split(',')]
        except ValueError:
            raise ValidationError("All values must be numerical")
        if len(data) > MAX_NUMBER_PARAMETERS:
            raise ValidationError("Cannot have more than {} elements".format(MAX_NUMBER_PARAMETERS))


class SimilarRecordingEvalForm(FlaskForm):
    choices = [("", "Select"), ("more similar", "More Similar"), ("accurate", "Accurate"), ("less similar", "Less Similar")]
    feedback = SelectField("Feedback", choices=choices)
    suggestion = TextAreaField("Suggestion")


class SimilarityEvaluationForm(FlaskForm):
    eval_list = FieldList(FormField(SimilarRecordingEvalForm), min_entries=10, max_entries=10)
