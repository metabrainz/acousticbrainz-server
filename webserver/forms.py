from wtforms import BooleanField, SelectField, StringField, TextAreaField
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


class DatasetCSVImportForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired("Dataset name is required")])
    description = TextAreaField("Description")
    file = FileField("CSV file", validators=[
        FileRequired(),
        FileAllowed(["csv"], "Dataset needs to be in CSV format"),
    ])


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

