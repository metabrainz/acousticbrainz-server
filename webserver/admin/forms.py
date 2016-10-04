from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, UUID
from webserver.forms import DynamicSelectField


class AddAdminForm(Form):
    musicbrainz_id = StringField(
        "MusicBrainz username",
        validators=[DataRequired("MusicBrainz username is required!")],
    )
    force = BooleanField("Create user if doesn't exist")


class EditChallengeForm(Form):
    name = StringField(
        "Name",
        validators=[DataRequired("Name of the challenge is required!")],
    )
    start_time = DateField(
        "Start time",
        validators=[DataRequired("Start time is required!")],
    )
    end_time = DateField(
        "End time",
        validators=[DataRequired("End time is required!")],
    )

    def __init__(self, default_name=None, default_start_time=None, default_end_time=None, **kwargs):
        kwargs.setdefault('name', default_name)
        kwargs.setdefault('start_time', default_start_time)
        kwargs.setdefault('end_time', default_end_time)
        Form.__init__(self, **kwargs)


class AddChallengeForm(EditChallengeForm):
    classes = StringField("Classes", validators=[DataRequired("List of classes is required!")])
    validation_dataset_id = DynamicSelectField("Validation dataset", choices=[],
                                               validators=[UUID("Incorrect validation dataset ID!")])
