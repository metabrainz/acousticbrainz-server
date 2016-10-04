from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, UUID
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from db import dataset_eval


DATASET_EVAL_NO_FILTER = "no_filtering"
DATASET_EVAL_LOCAL = "local"
DATASET_EVAL_REMOTE = "remote"

DATASET_PENDING = "pending"
DATASET_RUNNING = "running"
DATASET_DONE = "done"
DATASET_ALL = "all"

class DynamicSelectField(SelectField):
    """Select field for use with dynamic loader."""
    def pre_validate(self, form):
        pass


class _OptionalUUID(UUID):
    def __call__(self, form, field):
        if not field.data:
            return True
        message = self.message
        if message is None:
            message = field.gettext('Invalid UUID.')
        super(UUID, self).__call__(form, field, message)


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
    evaluation_location = SelectField("Evaluation location", choices=[
        (DATASET_EVAL_LOCAL, "Evaluate on acousticbrainz.org"),
        (DATASET_EVAL_REMOTE, "Evaluate on your own machine")],
        default = DATASET_EVAL_LOCAL
    )
    normalize = BooleanField("Normalize classes")
    challenge_id = DynamicSelectField("Challenge", choices=[],
                                      validators=[_OptionalUUID("Incorrect challenge ID!")])

