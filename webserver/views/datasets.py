from __future__ import absolute_import
from __future__ import division
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, Unauthorized, BadRequest
import webserver.external.musicbrainz_database.recording as mb_recording
import webserver.external.musicbrainz_database.exceptions as mb_exceptions
from webserver import flash, forms
from utils import dataset_validator
from collections import defaultdict
import db.exceptions
import db.dataset
import db.dataset_eval
import db.user
import csv
import math
import six

datasets_bp = Blueprint("datasets", __name__)

def _pagenum_to_offset(pagenum, limit):
    # Page number and limit to list elements
    # 3, 5 -> list[10:15]
    if pagenum < 1:
        return 0, limit

    start = (pagenum-1) * limit
    end = start + limit

    return start, end

def _make_pager(data, page, url, urlargs):
    DEFAULT_LIMIT = 10

    total = len(data)
    total_pages = int(math.ceil(total/DEFAULT_LIMIT))

    if page > total_pages:
        page = total_pages

    start, end = _pagenum_to_offset(page, DEFAULT_LIMIT)
    dataview = data[start:end]

    pages = []
    for p in range(1, total_pages+1):
        pages.append( (p, "%s?page=%s" % (url_for(url, **urlargs), p)) )

    prevpage = None
    if page > 1:
        prevpage = "%s?page=%s" % (url_for(url, **urlargs), page-1)
    nextpage = None
    if page < total_pages:
        nextpage = "%s?page=%s" % (url_for(url, **urlargs), page+1)

    return dataview, page, total_pages, prevpage, pages, nextpage

@datasets_bp.route("/list",  defaults={"status": "all"})
@datasets_bp.route("/list/<status>")
def list_datasets(status):
    if status != "all" and status not in db.dataset_eval.VALID_STATUSES:
        status = "all"

    page = request.args.get("page", 1)
    try:
        page = int(page)
    except ValueError:
        page = 1

    alldatasets = db.dataset.get_public_datasets(status)
    datasets, page, total_pages, prevpage, pages, nextpage = _make_pager(alldatasets,
            page, ".list_datasets", {"status": status})

    return render_template("datasets/list.html",
            datasets=datasets,
            status=status,
            page=page,
            pages=pages,
            total_pages=total_pages,
            prevpage=prevpage,
            nextpage=nextpage)


@datasets_bp.route("/<uuid:id>")
def view(id):
    ds = get_dataset(id)
    return render_template(
        "datasets/view.html",
        dataset=ds,
        author=db.user.get(ds["author"]),
    )


@datasets_bp.route("/accuracy")
def accuracy():
    return render_template("datasets/accuracy.html")


@datasets_bp.route("/<uuid:dataset_id>/evaluation")
def eval_info(dataset_id):
    ds = get_dataset(dataset_id)
    return render_template(
        "datasets/eval-info.html",
        dataset=ds,
        author=db.user.get(ds["author"]),
    )


@datasets_bp.route("/<uuid:dataset_id>/<uuid:job_id>", methods=["DELETE"])
def eval_job(dataset_id, job_id):
    # Getting dataset to check if it exists and current user is allowed to view it.
    ds = get_dataset(dataset_id)
    job = db.dataset_eval.get_job(job_id)
    if not job or job["dataset_id"] != ds["id"]:
        return jsonify({
            "success": False,
            "error": "Can't find evaluation job with a specified ID for this dataset.",
        }), 404

    if request.method == "DELETE":
        if not current_user.is_authenticated or ds["author"] != current_user.id:
            return jsonify({
                "success": False,
                "error": "You are not allowed to delete this evaluation job.",
            }), 401  # Unauthorized
        try:
            db.dataset_eval.delete_job(job_id)
        except db.exceptions.DatabaseException as e:
            return jsonify({
                "success": False,
                "error": str(e),
            }), 400  # Bad Request
        return jsonify({"success": True})


@datasets_bp.route("/<uuid:dataset_id>/evaluation/json")
def eval_jobs(dataset_id):
    # Getting dataset to check if it exists and current user is allowed to view it.
    ds = get_dataset(dataset_id)
    jobs = db.dataset_eval.get_jobs_for_dataset(ds["id"])
    # TODO(roman): Remove unused data ("confusion_matrix", "dataset_id").
    last_edited_time = ds["last_edited"]
    for job in jobs:
        if "result" in job and job["result"]:
            job['outdated'] = last_edited_time > job["created"]
            job["result"]["table"] = prepare_table_from_cm(job["result"]["confusion_matrix"])
    return jsonify({
        "jobs": jobs,
        "dataset": {
            "author": db.user.get(ds["author"]),
        }
    })


@datasets_bp.route("/<uuid:dataset_id>/evaluate", methods=('GET', 'POST'))
def evaluate(dataset_id):
    """Endpoint for submitting dataset for evaluation."""
    ds = get_dataset(dataset_id)
    if not ds["public"]:
        flash.warn("Can't add private datasets into evaluation queue.")
        return redirect(url_for(".eval_info", dataset_id=dataset_id))
    if db.dataset_eval.job_exists(dataset_id):
        flash.warn("Evaluation job for this dataset has been already created.")
        return redirect(url_for(".eval_info", dataset_id=dataset_id))

    form = forms.DatasetEvaluationForm()

    if form.validate_on_submit():
        try:
            if form.filter_type.data == forms.DATASET_EVAL_NO_FILTER:
                form.filter_type.data = None
            db.dataset_eval.evaluate_dataset(
                dataset_id=ds["id"],
                normalize=form.normalize.data,
                eval_location=form.evaluation_location.data,
                filter_type=form.filter_type.data,
            )
            flash.info("Dataset %s has been added into evaluation queue." % ds["id"])
        except db.dataset_eval.IncompleteDatasetException as e:
            flash.error("Cannot add this dataset because of a validation error: %s" % e)
        except db.dataset_eval.JobExistsException:
            flash.warn("An evaluation job for this dataset has been already created.")
        return redirect(url_for(".eval_info", dataset_id=dataset_id))

    return render_template("datasets/evaluate.html", dataset=ds, form=form)


@datasets_bp.route("/<uuid:id>/json")
def view_json(id):
    dataset = get_dataset(id)
    dataset_clean = {
        "name": dataset["name"],
        "description": dataset["description"],
        "classes": [],
        "public": dataset["public"],
    }
    for cls in dataset["classes"]:
        dataset_clean["classes"].append({
            "name": cls["name"],
            "description": cls["description"],
            "recordings": cls["recordings"],
        })
    return jsonify(dataset_clean)


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
            dataset_id = db.dataset.create_from_dict(dataset_dict, current_user.id)
        except dataset_validator.ValidationException as e:
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
    form = forms.DatasetCSVImportForm()
    if form.validate_on_submit():
        dataset_dict = {
            "name": form.name.data,
            "description": form.description.data,
            "classes": _parse_dataset_csv(request.files[form.file.name]),
            "public": True,
        }
        try:
            dataset_id = db.dataset.create_from_dict(dataset_dict, current_user.id)
        except dataset_validator.ValidationException as e:
            raise BadRequest(str(e))
        flash.info("Dataset has been imported successfully.")
        return redirect(url_for(".view", id=dataset_id))

    else:
        return render_template("datasets/import.html", form=form)


def _parse_dataset_csv(file):
    classes_dict = defaultdict(list)
    for class_row in csv.reader(file):
        if len(class_row) != 2:
            raise BadRequest("Bad dataset! Each row must contain one <MBID, class name> pair.")
        classes_dict[class_row[1]].append(class_row[0])
    classes = []
    for name, recordings in six.iteritems(classes_dict):
        classes.append({
            "name": name,
            "recordings": recordings,
        })
    return classes


@datasets_bp.route("/<uuid:dataset_id>/edit", methods=("GET", "POST"))
@login_required
def edit(dataset_id):
    ds = get_dataset(dataset_id)
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
            db.dataset.update(str(dataset_id), dataset_dict, current_user.id)
        except dataset_validator.ValidationException as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        return jsonify(
            success=True,
            dataset_id=dataset_id,
        )

    else:  # GET
        return render_template(
            "datasets/edit.html",
            mode="edit",
            dataset_id=str(dataset_id),
            dataset_name=ds["name"],
        )


@datasets_bp.route("/<uuid:dataset_id>/delete", methods=("GET", "POST"))
@login_required
def delete(dataset_id):
    ds = get_dataset(dataset_id)
    if ds["author"] != current_user.id:
        return jsonify(
            error=True,
            description="You can't delete this dataset.",
        ), 401  # Unauthorized

    if request.method == "POST":
        db.dataset.delete(ds["id"])
        flash.success("Dataset has been deleted.")
        return redirect(url_for("user.profile", musicbrainz_id=current_user.musicbrainz_id))
    else:  # GET
        return render_template("datasets/delete.html", dataset=ds)


def _get_recording_info_for_mbid(mbid):
    try:
        recording = mb_recording.get_recording_by_id(mbid)
        return jsonify(recording={
            "title": recording["title"],
            "artist": recording["artist-credit-phrase"],
        })
    except mb_exceptions.NoDataFoundException as e:
        return jsonify(error=str(e)), 404


@datasets_bp.route("/metadata/recording/<uuid:mbid>")
@login_required
def recording_info(mbid):
    """Endpoint for getting information about recordings (title and artist)."""
    return _get_recording_info_for_mbid(mbid)


@datasets_bp.route("/metadata/dataset/<uuid:dataset_id>/<uuid:mbid>")
def recording_info_in_dataset(dataset_id, mbid):
    """Endpoint for getting information about recordings (title and artist), for the
    case when user is not logged in.
    Args:
        mbid (uuid): the recording mbid for which info is to be returned
        dataset_id (uuid): the dataset id to which the passed recording mbid belongs
    Returns:
        json: If the mbid is present in the dataset, info about the recording
              404 otherwise
     """
    if not db.dataset.check_recording_in_dataset(dataset_id, mbid):
        return jsonify(error="Recording not found in the dataset"), 404
    return _get_recording_info_for_mbid(mbid)


def get_dataset(dataset_id):
    """Wrapper for `dataset.get` function in `db` package.
    Checks the following conditions and raises NotFound exception if they
    aren't met:
    * Specified dataset exists.
    * Current user is allowed to access this dataset.
    """
    try:
        ds = db.dataset.get(dataset_id)
    except db.exceptions.NoDataFoundException as e:
        raise NotFound("Can't find this dataset.")
    if ds["public"] or (current_user.is_authenticated and
                        ds["author"] == current_user.id):
        return ds
    else:
        raise NotFound("Can't find this dataset.")


def prepare_table_from_cm(confusion_matrix):
    """Prepares data for table to visualize confusion matrix from Gaia.
    This works with modified version of confusion matrix that we store in our
    database (we store number of recordings in each predicted class instead of
    actual UUIDs of recordings). See gaia_wrapper.py in dataset_eval package
    for implementation details.
    """
    all_classes = set()
    dataset_size = 0  # Number of recordings in the dataset
    for actual_cls in confusion_matrix:
        all_classes.add(actual_cls)
        for predicted_cls in confusion_matrix[actual_cls]:
            # Need to add to class list from there as well because some classes
            # might be missing from the outer dictionary.
            all_classes.add(predicted_cls)
            dataset_size += confusion_matrix[actual_cls][predicted_cls]

    # Sorting to be able to match columns in the table.
    all_classes = sorted(all_classes)

    table_data = {
        "classes": all_classes,
        "rows": [],
    }

    for actual in all_classes:
        # Counting how many tracks were associated with that class during classification
        predicted_class_size = 0
        for predicted in confusion_matrix[actual].values():
            predicted_class_size += predicted

        row = {
            "total": predicted_class_size,
            "proportion": predicted_class_size * 100.0 / dataset_size,
            "predicted": [],
        }

        for predicted in all_classes:
            current_cls = {
                "count": 0,
                "percentage": 0,
            }
            if actual in confusion_matrix:
                if predicted in confusion_matrix[actual]:
                    current_cls["count"] = confusion_matrix[actual][predicted]
                    current_cls["percentage"] = current_cls["count"] * 100.0 / predicted_class_size
            row["predicted"].append(current_cls)

        table_data["rows"].append(row)

    return table_data
