import json

from flask import render_template, Blueprint, current_app
from flask.helpers import url_for

from application.googlesheetscollector import get_datasets


base = Blueprint("base", __name__)


@base.context_processor
def set_globals():
    return {"staticPath": "https://digital-land.github.io"}


def read_json_file(data_file_path):
    f = open(
        data_file_path,
    )
    data = json.load(f)
    f.close()
    return data


@base.route("/")
@base.route("/index")
def index():
    return render_template("index.html")


@base.route("/performance")
def performance():
    datasets = get_datasets()
    print("DATASETS")
    print(len(datasets))
    return render_template("performance.html", info_page=True, datasets=datasets)


@base.route("/performance/info")
def performance_info():
    data = read_json_file("application/data/info/performance.json")
    return render_template(
        "info.html",
        page_title="Digital land team performance",
        page_url=url_for("base.performance"),
        data=data,
    )


@base.route("/dataset/<dataset_name>/performance")
def dataset_performance(dataset_name):
    return render_template("dataset/performance.html", name=dataset_name)


@base.route("/organisation/<organisation>/performance")
def organisation_performance(organisation):
    return render_template("organisation/performance.html", organisation=organisation)


@base.route("/resource/<resource>/performance")
def resource_performance(resource):
    return render_template("resource/performance.html", resource=resource)
