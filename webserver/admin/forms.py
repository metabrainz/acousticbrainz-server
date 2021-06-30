from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired


class AddAdminForm(FlaskForm):
    musicbrainz_id = StringField(
        "MusicBrainz username",
        validators=[DataRequired("MusicBrainz username is required!")],
    )
    force = BooleanField("Create user if doesn't exist")
