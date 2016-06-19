from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired


class AddAdminForm(Form):
    musicbrainz_id = StringField(
        "MusicBrainz username",
        validators=[DataRequired("MusicBrainz username is required!")],
    )
    force = BooleanField("Create user if doesn't exist")
