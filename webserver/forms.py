from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from db import dataset_eval


DATASET_EVAL_NO_FILTER = "no_filtering"
DATASET_PENDING = "pending"
DATASET_RUNNING = "running"
DATASET_DONE = "done"
DATASET_ALL = "all"

class DatasetCSVImportForm(Form):
    name = StringField("Name", validators=[DataRequired("Dataset name is required!")])
    description = TextAreaField("Description")
    file = FileField("CSV file", validators=[
        FileRequired(),
        FileAllowed(["csv"], "Dataset needs to be in CSV format!"),
    ])


class DatasetEvaluationForm(Form):
    filter_type = SelectField("Filtering", choices=[
        (DATASET_EVAL_NO_FILTER, "Don't filter"),
        (dataset_eval.FILTER_ARTIST, "By Artist"),
    ])
    normalize = BooleanField("Normalize classes")

class DatasetListForm(Form):
    filter_type = SelectField("Dataset Evaluation Status", choices=[
        (DATASET_PENDING, "Pending"),
        (DATASET_RUNNING, "Running"),
        (DATASET_DONE, "Done"),
        (DATASET_ALL, "All"),
    ])

