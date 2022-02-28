import json
from datetime import datetime

from flask import render_template, Blueprint, current_app, redirect
from flask.helpers import url_for
from flask import request

from application.datasette import (
    get_monthly_counts,
    publisher_counts,
    publisher_coverage,
    active_resources,
    sources_by_dataset,
    resources_by_dataset,
    get_source,
    get_datasets_summary,
    get_resource_count,
    total_publisher_coverage,
    content_type_counts,
    resources_of_type,
    get_resources,
    get_resource,
    entry_count,
    source_count_per_organisation,
    get_theme,
    get_typology,
    dataset_latest_logs,
    DLDatasette,
)
from application.data_access.entity_queries import (
    fetch_entity_count,
    fetch_organisation_entities_using_end_dates,
)
from application.data_access.digital_land_queries import (
    fetch_datasets,
    fetch_log_summary,
    fetch_sources,
    fetch_organisation_stats,
    fetch_source_counts,
    fetch_latest_resource,
)

from application.utils import (
    resources_per_publishers,
    index_by,
    recent_dates,
    read_json_file,
    yesterday,
)


base = Blueprint("base", __name__)


@base.context_processor
def set_globals():
    return {"staticPath": "https://digital-land.github.io"}


###################
# Service homepage
###################


@base.route("/")
@base.route("/index")
def index():
    return render_template("index.html")


####################
# Overview dashboard
####################


@base.route("/performance")
@base.route("/performance/")
def performance():
    ds = DLDatasette()
    gs_datasets = get_datasets_summary()
    entity_counts = fetch_entity_count()

    return render_template(
        "performance.html",
        info_page=url_for("base.performance_info"),
        datasets=gs_datasets,
        stats=get_monthly_counts(),
        publisher_count=total_publisher_coverage(),
        source_counts=fetch_source_counts(),
        entity_count=ds.get_entity_count(),
        datasets_with_data_count=len(entity_counts.keys()),
        resource_count=get_resource_count(),
        publisher_using_enddate_count=len(
            fetch_organisation_entities_using_end_dates()
        ),
        content_type_counts=content_type_counts(),
        new_resources=ds.get_new_resources(dates=recent_dates(7)),
    )


@base.route("/performance/info")
def performance_info():
    data = read_json_file("application/data/info/performance.json")
    return render_template(
        "info.html",
        page_title="Digital land team performance",
        page_url=url_for("base.performance"),
        data=data,
    )


##########
# Datasets
##########


@base.route("/dataset")
def datasets():
    filters = {}
    # if request.args.get("active"):
    #     filters["active"] = request.args.get("active")
    if request.args.get("theme"):
        filters["theme"] = request.args.get("theme")
    if request.args.get("typology"):
        filters["typology"] = request.args.get("typology")

    if len(filters.keys()):
        dataset_records = fetch_datasets(filter=filters)
    else:
        dataset_records = fetch_datasets()

    return render_template(
        "dataset/index.html",
        datasets=dataset_records,
        filters=filters,
        filter_btns=filter_off_btns(filters),
        themes=get_theme(),
        typologies=get_typology(),
    )


@base.route("/dataset/<dataset>")
def dataset(dataset):
    ds = DLDatasette()
    datasets = get_datasets_summary()
    dataset_name = dataset
    dataset = [v for k, v in datasets.items() if v.get("pipeline") == dataset]

    resources_by_publisher = resources_per_publishers(active_resources(dataset_name))

    publishers = publisher_counts(dataset_name)
    publisher_splits = {"active": [], "noactive": []}
    for k, publisher in publishers.items():
        if publisher["active_resources"] == 0:
            publisher_splits["noactive"].append(publisher)
        else:
            publisher_splits["active"].append(publisher)

    # for the active resource charts
    resource_stats = {
        "over_one": len(
            [p for p in resources_by_publisher if len(resources_by_publisher[p]) > 1]
        ),
        "one": len(
            [p for p in resources_by_publisher if len(resources_by_publisher[p]) == 1]
        ),
        "zero": len(publisher_splits["noactive"]),
    }

    resource_count = (
        resources_by_dataset(dataset_name)[0]
        if resources_by_dataset(dataset_name)
        else 0
    )

    sources_no_doc_url, query_url = fetch_sources(
        limit=500, filter={"documentation_url": "", "pipeline": dataset_name}
    )

    return render_template(
        "dataset/performance.html",
        name=dataset_name,
        info_page=url_for("base.dataset_info", dataset=dataset_name),
        dataset=dataset[0] if len(dataset) else "",
        latest_resource=fetch_latest_resource(dataset_name),
        monthly_counts=get_monthly_counts(pipeline=dataset_name),
        publishers=publisher_splits,
        today=datetime.utcnow().isoformat()[:10],
        entity_count=ds.get_entity_count(pipeline=dataset_name),
        resource_count=resource_count,
        coverage=publisher_coverage(dataset_name)[0],
        resource_stats=resource_stats,
        sources_no_doc_url=sources_no_doc_url,
        content_type_counts=content_type_counts(dataset_name),
        latest_logs=dataset_latest_logs(),
        blank_sources=ds.get_blank_sources(dataset_name),
        source_count=ds.source_counts(pipeline=dataset_name),
    )


@base.route("/dataset/<dataset>/info")
def dataset_info(dataset):
    data = read_json_file("application/data/info/dataset.json")
    return render_template(
        "info.html",
        page_title=dataset + " performance",
        page_url=url_for("base.dataset_performance", dataset_name=dataset),
        data=data,
    )


###########
# Resources
###########


def filter_off_btns(filters):
    # used by all index pages with filter options
    btns = []
    for filter, value in filters.items():
        filters_copy = filters.copy()
        del filters_copy[filter]
        btns.append({"filter": filter, "value": value, "url_params": filters_copy})
    return btns


@base.route("/resource")
def resources():
    filters = {}
    if request.args.get("pipeline"):
        filters["pipeline"] = request.args.get("pipeline")
    if request.args.get("content_type"):
        filters["content_type"] = request.args.get("content_type")
    if request.args.get("organisation"):
        filters["organisation"] = request.args.get("organisation")
    if request.args.get("resource"):
        filters["resource"] = request.args.get("resource")

    resources_per_dataset = index_by("pipeline", resources_by_dataset())

    if len(filters.keys()):
        resource_records = get_resources(filter=filters)
    else:
        resource_records = get_resources()

    return render_template(
        "resource/index.html",
        by_dataset=resources_per_dataset,
        resource_count=get_resource_count(),
        content_type_counts=content_type_counts(),
        datasets=fetch_entity_count(),
        resources=resource_records,
        filters=filters,
        filter_btns=filter_off_btns(filters),
        organisations=fetch_organisation_stats(),
    )


@base.route("/resource/<resource>")
def resource(resource):
    resource_data = get_resource(resource)
    dataset = resource_data[0]["pipeline"].split(";")[0]
    return render_template(
        "resource/resource.html",
        resource=resource_data,
        info_page=url_for("base.resource_info", resource=resource),
        entry_count=entry_count(dataset, resource),
    )


@base.route("/resource/<resource>/info")
def resource_info(resource):
    data = read_json_file("application/data/info/resource.json")
    return render_template(
        "info.html",
        page_title="Resource performance",
        page_url=url_for("base.resource", resource=resource),
        data=data,
    )


#########
# Sources
#########


def paramify(url):
    # there was a problem if the url to search on included url params
    # this can be avoid if all & are replaced with %26
    url = url.replace("&", "%26")
    # replace spaces (' ' or '%20' ) with %2520 - datasette automatically decoded %20
    url = url.replace(" ", "%2520")
    return url.replace("%20", "%2520")


@base.route("/source")
def sources():
    ds = DLDatasette()
    filters = {}
    if request.args.get("pipeline"):
        filters["pipeline"] = request.args.get("pipeline")
    if request.args.get("organisation") is not None:
        filters["organisation"] = request.args.get("organisation")
    if request.args.get("endpoint_url"):
        filters["endpoint_url"] = paramify(request.args.get("endpoint_url"))
    if request.args.get("endpoint_"):
        filters["endpoint_"] = request.args.get("endpoint_")
    if request.args.get("source"):
        filters["source"] = request.args.get("source")
    if request.args.get("documentation_url") is not None:
        filters["documentation_url"] = request.args.get("documentation_url")
    include_blanks = False
    if request.args.get("include_blanks") is not None:
        include_blanks = request.args.get("include_blanks")

    datasets = sources_by_dataset()
    organisations = source_count_per_organisation()

    if len(filters.keys()):
        source_records, query_url = fetch_sources(
            filter=filters, include_blanks=include_blanks
        )
    else:
        source_records, query_url = fetch_sources(include_blanks=include_blanks)

    return render_template(
        "source/index.html",
        by_dataset=datasets,
        counts=ds.source_counts()[0],
        sources=source_records,
        filters=filters,
        filter_btns=filter_off_btns(filters),
        organisations=organisations,
        query_url=query_url,
        include_blanks=include_blanks,
    )


@base.route("/source/<source>")
def source(source):
    source_data = get_source(source)
    return render_template(
        "source/source.html",
        source=source_data[0],
        resources=get_resources(filter={"source": source}),
    )


###############
# Content-types
###############


@base.route("/content-type")
def content_types():
    pipeline = request.args.get("pipeline")

    if pipeline:
        return render_template(
            "content_type/index.html",
            content_type_counts=content_type_counts(pipeline),
            pipeline=pipeline,
        )

    return render_template(
        "content_type/index.html", content_type_counts=content_type_counts()
    )


@base.route("/content-type/<content_type>")
def content_type(content_type):

    return render_template(
        "content_type/type.html",
        content_type=content_type,
        resources=resources_of_type(content_type),
    )


######
# Logs
######


@base.route("/logs")
def logs():
    ds = DLDatasette()

    if (
        request.args.get("log-date-day")
        and request.args.get("log-date-month")
        and request.args.get("log-date-year")
    ):
        d = f"{request.args.get('log-date-year')}-{request.args.get('log-date-month')}-{request.args.get('log-date-day')}"
        return redirect(url_for("base.log", date=d))

    summary = fetch_log_summary()

    return render_template(
        "logs/logs.html",
        summary=summary,
        resources=ds.get_new_resources(),
        yesterday=yesterday(string=True),
        endpoint_count=sum([status["count"] for status in summary]),
    )


@base.route("/logs/<date>")
def log(date):
    ds = DLDatasette()

    summary = fetch_log_summary(date=date)

    return render_template(
        "logs/logs.html",
        summary=summary,
        resources=ds.get_new_resources(dates=[date]),
        date=date,
        endpoint_count=sum([status["count"] for status in summary]),
    )
