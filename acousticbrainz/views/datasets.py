from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired
from werkzeug.exceptions import NotFound, Unauthorized, BadRequest
from acousticbrainz.data import dataset, user as user_data
from acousticbrainz.external import musicbrainz
from acousticbrainz import flash
import jsonschema
import csv

datasets_bp = Blueprint("datasets", __name__)


@datasets_bp.route("/<uuid:id>")
def view(id):
    ds = dataset.get(id)
    if not ds or (not ds["public"] and (not current_user.is_authenticated() or ds["author"] != current_user.id)):
        raise NotFound("Can't find this dataset.")
    return render_template(
        "datasets/view.html",
        dataset=ds,
        author=user_data.get(ds["author"]),
    )


@datasets_bp.route("/<uuid:id>/json")
def view_json(id):
    ds = dataset.get(id)
    if not ds or (not ds["public"] and (not current_user.is_authenticated() or ds["author"] != current_user.id)):
        raise NotFound("Can't find this dataset.")
    return jsonify(ds)


@datasets_bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        dataset_dict = request.get_json()
        if not dataset_dict:
            return jsonify(
                success=False,
                error="Data must be submitted in JSON format.",
            ), 400

        try:
            dataset_id = dataset.create_from_dict(dataset_dict, current_user.id)
        except jsonschema.ValidationError as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        return jsonify(
            success=True,
            dataset_id=dataset_id,
        )

    else:  # GET
        return render_template("datasets/edit.html", mode="create")


@datasets_bp.route("/import", methods=("GET", "POST"))
@login_required
def import_csv():
    form = CSVImportForm()
    if form.validate_on_submit():
        dataset_dict = {
            "name": form.name.data,
            "description": form.description.data,
            "classes": _parse_dataset_csv(request.files[form.file.name]),
            "public": False,
        }
        try:
            dataset_id = dataset.create_from_dict(dataset_dict, current_user.id)
        except jsonschema.ValidationError as e:
            raise BadRequest(str(e))
        flash.info("Dataset has been imported successfully.")
        return redirect(url_for(".edit", id=dataset_id))

    else:
        return render_template("datasets/import.html", form=form)


def _parse_dataset_csv(file):
    classes = []
    for class_row in csv.reader(file):
        if not class_row:
            pass  # Skipping empty row
        classes.append({
            "name": class_row[0],
            "recordings": class_row[1:],
        })
    return classes


@datasets_bp.route("/<uuid:id>/edit", methods=("GET", "POST"))
@login_required
def edit(id):
    ds = dataset.get(id)
    if not ds or (not ds["public"] and ds["author"] != current_user.id):
        raise NotFound("Can't find this dataset.")
    if ds["author"] != current_user.id:
        raise Unauthorized("You can't edit this dataset.")

    if request.method == "POST":
        dataset_dict = request.get_json()
        if not dataset_dict:
            return jsonify(
                success=False,
                error="Data must be submitted in JSON format.",
            ), 400

        try:
            dataset.update(str(id), dataset_dict, current_user.id)
        except jsonschema.ValidationError as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        return jsonify(
            success=True,
            dataset_id=id,
        )

    else:  # GET
        return render_template(
            "datasets/edit.html",
            mode="edit",
            dataset_id=str(id),
            dataset_name=ds["name"],
        )


@datasets_bp.route("/<uuid:id>/delete", methods=("GET", "POST"))
@login_required
def delete(id):
    ds = dataset.get(id)
    if not ds or (not ds["public"] and ds["author"] != current_user.id):
        raise NotFound("Can't find this dataset.")
    if ds["author"] != current_user.id:
        raise Unauthorized("You can't delete this dataset.")

    if request.method == "POST":
        dataset.delete(ds["id"])
        flash.success("Dataset has been deleted.")
        return redirect(url_for("user.profile", musicbrainz_id=current_user.musicbrainz_id))
    else:  # GET
        return render_template("datasets/delete.html", dataset=ds)


@datasets_bp.route("/recording/<uuid:mbid>")
@login_required
def recording_info(mbid):
    """Endpoint for getting information about recordings (title and artist)."""
    try:
        recording = musicbrainz.get_recording_by_id(mbid)
        return jsonify(recording={
            "title": recording["title"],
            "artist": recording["artist-credit-phrase"],
        })
    except musicbrainz.DataUnavailable as e:
        return jsonify(error=str(e)), 404


class CSVImportForm(Form):
    name = StringField("Name", validators=[DataRequired("Dataset name is required!")])
    description = TextAreaField("Description")
    file = FileField("CSV file", validators=[
        FileRequired(),
        FileAllowed(["csv"], "Dataset needs to be in CSV format!"),
    ])
