from wtforms import BooleanField, SelectField, StringField, TextAreaField, \
    validators, SelectMultipleField, widgets
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

DATASET_C_VALUE = '-5, -3, -1, 1, 3, 5, 7, 9, 11'
DATASET_GAMMA_VALUE = '3, 1, -1, -3, -5, -7, -9, -11'
# MultiCheckboxField take multiple field values
PREPROCESSING_VALUES = [('basic', 'basic'), ('lowlevel', 'lowlevel'), ('nobands', 'nobands'),
                        ('normalized', 'normalized'), ('gaussianized', 'gaussianized')
]


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
    filter_type = SelectField("Filtering", choices=[
        (DATASET_EVAL_NO_FILTER, "Don't filter"),
        (dataset_eval.FILTER_ARTIST, "By Artist"),
    ])
    evaluation_location = SelectField("Evaluation location", choices=[
        (DATASET_EVAL_LOCAL, "Evaluate on acousticbrainz.org"),
        (DATASET_EVAL_REMOTE, "Evaluate on your own machine")],
        default = DATASET_EVAL_LOCAL
    )
    normalize = BooleanField("Normalize classes")

    # Add three more preferences for c, gamma and preprocessing values
    c_value = TextAreaField('C Values',
        default=DATASET_C_VALUE
    )
    gamma_value = TextAreaField('Gamma Values',
        default=DATASET_GAMMA_VALUE
    )
    preprocessing_values = MultiCheckboxField('Preprocessing Values',
        choices=PREPROCESSING_VALUES
    )
