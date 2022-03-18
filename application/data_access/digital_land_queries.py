import logging
import urllib.parse

from application.caching import get
from application.utils import create_dict, yesterday, index_by
from application.data_access.sql_helpers import (
    generate_sql_where_str,
    prepare_query_str,
)

logger = logging.getLogger(__name__)

DATASETTE_URL = "https://datasette.digital-land.info"
DATABASE_NAME = "digital-land"


def fetch_datasets(filter=None):
    params = ""
    where_clause = ""
    # handle any filters
    if filter:
        where_clause, params = generate_sql_where_str(
            filter,
            {
                "active": "dataset_active",  # not currently available
                "dataset": "dataset.dataset",
                "theme": "dataset_theme.theme",
            },
        )

    query_lines = [
        "SELECT",
        "dataset.*,",
        "GROUP_CONCAT(dataset_theme.theme, ';') AS themes",
        "FROM dataset",
        "INNER JOIN dataset_theme ON dataset.dataset = dataset_theme.dataset",
        where_clause,
    ]

    query_lines.append("GROUP BY dataset.dataset")
    query_str = " ".join(query_lines)
    query = urllib.parse.quote(query_str)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}{params}"
    # logger.info("get_datasets: %s", url)
    print("get_datasets: {}".format(url))
    result = get(url, format="json")

    if filter and "dataset" in filter.keys():
        return create_dict(result["columns"], result["rows"][0])
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_sources(limit=100, filter=None, include_blanks=False, concat_pipelines=True):
    params = ""
    limit_str = ""
    where_clause = ""

    # handle limit
    if limit:
        limit_str = "limit {}".format(limit)

    # handle any filters
    if filter:
        where_clause, params = generate_sql_where_str(
            filter,
            {
                "organisation": "source.organisation",
                "endpoint_": "endpoint.endpoint",
                "source": "source.source",
            },
        )

    # handle case where blanks also included
    if not include_blanks:
        where_clause = (
            where_clause
            + ("WHERE " if where_clause == "" else " AND ")
            + 'source.endpoint != ""'
        )

    # handle concat of pipelines for each source
    group_pipeline_strs = "source_pipeline.pipeline"
    group_by = ""
    if concat_pipelines:
        group_pipeline_strs = (
            "GROUP_CONCAT(DISTINCT source_pipeline.pipeline) AS pipeline"
        )
        group_by = "GROUP BY source.source"

    query_lines = [
        "SELECT",
        "source.source,",
        "source.organisation,",
        "organisation.name,",
        "source.endpoint,",
        "source.documentation_url,",
        "source.entry_date,",
        "source.start_date,",
        "source.end_date,",
        group_pipeline_strs,
        "FROM",
        "source",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        "INNER JOIN organisation ON source.organisation = organisation.organisation",
        "INNER JOIN endpoint ON source.endpoint = endpoint.endpoint"
        if filter and "endpoint_" in filter.keys()
        else "",
        where_clause,
        group_by,
        "ORDER BY source.start_date DESC",
        limit_str,
    ]
    query_str = " ".join(query_lines)
    query = urllib.parse.quote(query_str)
    url = f"{DATASETTE_URL}/digital-land.json?sql={query}{params}"

    print(url)
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]], url.replace(
        "digital-land.json?sql", "digital-land?sql"
    )


def fetch_publishers():
    query_lines = [
        "SELECT",
        "source.organisation,",
        "organisation.name,",
        "organisation.end_date AS organisation_end_date,",
        "SUM(CASE WHEN (source.endpoint) is not null and (source.endpoint) != '' THEN 1 ELSE 0 END)  AS sources_with_endpoint",
        "FROM",
        "source",
        "INNER JOIN organisation ON source.organisation = organisation.organisation",
        "GROUP BY",
        "source.organisation",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_publishers: {url}")
    result = get(url, format="json")
    organisations = [create_dict(result["columns"], row) for row in result["rows"]]
    return index_by("organisation", organisations)


def f_orgs():
    query = urllib.parse.quote(
        "select name, organisation from organisation order by organisation"
    )
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    result = get(url, format="json")
    return [{"text": o[0], "value": o[1]} for o in result["rows"]]


def fetch_organisation_stats():
    """
    Returns a list of organisations with:
    - end_date if applicable
    - number of resources
    - number of resource without an end-date
    - number of endpoints
    - number of dataset resources are for
    """
    query_lines = [
        "SELECT",
        "organisation.name,",
        "source.organisation,",
        "organisation.end_date AS organisation_end_date,",
        "COUNT(DISTINCT resource.resource) AS resources,",
        "COUNT(",
        "DISTINCT CASE",
        "WHEN resource.end_date == '' THEN resource.resource",
        "WHEN strftime('%Y%m%d', resource.end_date) >= strftime('%Y%m%d', 'now') THEN resource.resource",
        "END",
        ") AS active,",
        "COUNT(DISTINCT resource_endpoint.endpoint) AS endpoints,",
        "COUNT(DISTINCT source_pipeline.pipeline) AS pipelines",
        "FROM",
        "resource",
        "INNER JOIN resource_endpoint ON resource.resource = resource_endpoint.resource",
        "INNER JOIN endpoint ON resource_endpoint.endpoint = endpoint.endpoint",
        "INNER JOIN source ON resource_endpoint.endpoint = source.endpoint",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        "INNER JOIN organisation ON source.organisation = organisation.organisation",
        "GROUP BY",
        "source.organisation",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_organisation_stats: {url}")
    result = get(url, format="json")
    organisations = [create_dict(result["columns"], row) for row in result["rows"]]
    return index_by("organisation", organisations)


def fetch_resources(filters=None, limit=None):
    limit_str = ""
    if limit:
        limit_str = f"LIMIT {limit}"

    where_clause = ""
    params = ""
    if filters:
        where_clause, params = generate_sql_where_str(
            filters,
            {
                "organisation": "source.organisation",
                "dataset": "source_pipeline.pipeline",
            },
        )

    query_lines = [
        "SELECT",
        "resource.resource,",
        "resource.entry_date,",
        "resource.start_date,",
        "resource.end_date,",
        "source.source,",
        "resource_endpoint.endpoint,",
        "endpoint.endpoint_url,",
        "source.organisation,",
        "source_pipeline.pipeline",
        "FROM",
        "resource",
        "INNER JOIN resource_endpoint ON resource.resource = resource_endpoint.resource",
        "INNER JOIN endpoint ON resource_endpoint.endpoint = endpoint.endpoint",
        "INNER JOIN source ON resource_endpoint.endpoint = source.endpoint",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        where_clause,
        "ORDER BY",
        "resource.start_date DESC",
        limit_str,
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}{params}"
    print(f"get_resources ({filters}): {url}")
    return get(url, format="json")


def fetch_resource(resource_hash):
    # seems like overkill...
    query_lines = [
        "SELECT",
        "DISTINCT resource.resource,",
        "resource.entry_date,",
        "resource.start_date,",
        "resource.end_date,",
        "resource_organisation.organisation,",
        "organisation.name,",
        "endpoint.endpoint,",
        "endpoint.endpoint_url,",
        "REPLACE(GROUP_CONCAT(DISTINCT log.content_type), ',', ';') AS content_type,",
        "REPLACE(GROUP_CONCAT(DISTINCT source_pipeline.pipeline), ',', ';') AS pipeline",
        "FROM",
        "resource",
        "INNER JOIN resource_organisation ON resource.resource = resource_organisation.resource",
        "INNER JOIN organisation ON resource_organisation.organisation = organisation.organisation",
        "INNER JOIN resource_endpoint ON resource.resource = resource_endpoint.resource",
        "INNER JOIN endpoint ON resource_endpoint.endpoint = endpoint.endpoint",
        "INNER JOIN log ON resource.resource = log.resource",
        "INNER JOIN source ON source.endpoint = resource_endpoint.endpoint",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        f"WHERE resource.resource = '{resource_hash}'",
        "GROUP BY",
        "endpoint.endpoint",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_resource {url}")
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_total_resource_count():
    query_lines = ["select count(distinct resource) from resource"]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_resource_count {url}")
    result = get(url, format="json")
    return result["rows"][0][0]


def fetch_latest_resource(dataset=None):
    if dataset:
        results = fetch_resources(filters={"dataset": dataset}, limit=1)
    else:
        results = fetch_resources(limit=1)

    if len(results["rows"]):
        return create_dict(results["columns"], results["rows"][0])

    return None


def fetch_resource_count_per_dataset(organisation=None):
    query_lines = [
        "SELECT",
        "COUNT(DISTINCT resource.resource) AS resources,",
        "COUNT(DISTINCT CASE ",
        "WHEN resource.end_date == '' THEN resource.resource",
        "WHEN strftime('%Y%m%d', resource.end_date) >= strftime('%Y%m%d', 'now') THEN resource.resource",
        "END) AS active_resources,",
        "COUNT(DISTINCT CASE",
        "WHEN resource.end_date != ''",
        "AND strftime('%Y%m%d', resource.end_date) <= strftime('%Y%m%d', 'now') THEN resource.resource",
        "END",
        ") AS ended_resources,",
        "COUNT(DISTINCT resource_endpoint.endpoint) AS endpoints,",
        "source_pipeline.pipeline AS pipeline",
        "FROM",
        "resource",
        "INNER JOIN resource_endpoint ON resource.resource = resource_endpoint.resource",
        "INNER JOIN endpoint ON resource_endpoint.endpoint = endpoint.endpoint",
        "INNER JOIN source ON resource_endpoint.endpoint = source.endpoint",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        "INNER JOIN organisation ON source.organisation = organisation.organisation",
        f"WHERE organisation.organisation = '{organisation}'" if organisation else "",
        "GROUP BY",
        "source.organisation," if organisation else "",
        "source_pipeline.pipeline",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_resource_count_per_dataset ({organisation}): {url}")
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_organisation_sources(organisation):
    sources, url = fetch_sources(
        filter={"organisation": organisation},
        include_blanks=True,
        concat_pipelines=False,
    )
    return sources


def fetch_overall_source_counts():
    query_lines = [
        "SELECT",
        "source_pipeline.pipeline,",
        "COUNT(DISTINCT source.source) AS sources,",
        "SUM(",
        "CASE",
        "WHEN (source.endpoint) is not null",
        "and (source.endpoint) != '' THEN 1",
        "ELSE 0",
        "END",
        ") AS sources_with_endpoint,",
        "SUM(",
        "CASE",
        "WHEN (source.endpoint) is not null",
        "and (source.endpoint) != '' and ((source.documentation_url) is null",
        "or (source.documentation_url) == '') THEN 1",
        "ELSE 0",
        "END",
        ") AS sources_missing_document_url",
        "FROM",
        "source",
        "INNER JOIN source_pipeline on source.source = source_pipeline.source",
        "GROUP BY",
        "source_pipeline.pipeline",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_source_counts (Overall): {url}")
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_organisation_source_counts(organisation):
    query_lines = [
        "SELECT",
        "source_pipeline.pipeline AS pipeline,",
        "COUNT(DISTINCT source.source) AS sources,",
        "SUM(CASE WHEN (source.endpoint) is not null and (source.endpoint) != ''",
        " THEN 1 ELSE 0 END)  AS sources_with_endpoint",
        "FROM",
        "source",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        "WHERE",
        f"source.organisation = '{organisation}'",
        "GROUP BY",
        "source_pipeline.pipeline",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_source_counts ({organisation}): {url}")
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_source_counts(organisation=None):
    if organisation:
        return fetch_organisation_source_counts(organisation)
    return fetch_overall_source_counts()


def fetch_latest_collector_run_date(dataset=None):
    where_clause = ""
    if dataset:
        where_clause = f"WHERE source_pipeline.pipeline = '{dataset}'"
    query_lines = [
        "SELECT",
        "source_pipeline.pipeline,",
        "MAX(log.entry_date) AS latest_attempt",
        "FROM",
        "source",
        "INNER JOIN source_pipeline ON source.source = source_pipeline.source",
        "INNER JOIN log ON source.endpoint = log.endpoint",
        where_clause,
        "GROUP BY",
        "source_pipeline.pipeline",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_latest_collector_run_date")
    result = get(url, format="json")
    return index_by(
        "pipeline", [create_dict(result["columns"], row) for row in result["rows"]]
    )


def fetch_table(tablename):
    url = f"{DATASETTE_URL}/{DATABASE_NAME}/{tablename}.json"
    print(f"get {tablename}", url)
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_themes():
    return fetch_table("theme")


def fetch_typologies():
    return fetch_table("typology")


##########################################
# Queries using log table as primary table
##########################################


def fetch_logs(filters=None, group_by=None):
    where_str = ""
    if filters:
        where_str = "WHERE " + " AND ".join(
            [f"log.{fil} = '{val}'" for fil, val in filters.items()]
        )

    group_by_str = ""
    if group_by:
        group_by_str = f"GROUP BY log.{group_by}"

    query_lines = ["SELECT", "log.*", "FROM", "log", where_str, group_by_str]

    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_logs", query)
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_log_summary(date=yesterday(string=True)):
    query_lines = [
        "SELECT",
        "entry_date,",
        "status,",
        "COUNT(DISTINCT endpoint) AS count",
        "FROM",
        "log",
        "WHERE",
        f"entry_date = '{date}'",
        "GROUP BY",
        "status",
    ]
    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    logger.info("get_log_summary: %s", url)
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]


def fetch_content_type_counts(dataset=None):
    joins = []
    where_str = None
    if dataset:
        joins = [
            "INNER JOIN source ON log.endpoint = source.endpoint",
            "INNER JOIN source_pipeline on source.source = source_pipeline.source",
        ]
        where_str = f"source_pipeline.pipeline = '{dataset}'"

    query_lines = [
        "SELECT",
        "log.content_type,",
        "count(DISTINCT log.resource) AS resource_count",
        "FROM",
        "log",
        *joins,
        "WHERE " + where_str if where_str is not None else "",
        "GROUP BY",
        "log.content_type",
    ]

    query = prepare_query_str(query_lines)
    url = f"{DATASETTE_URL}/{DATABASE_NAME}.json?sql={query}"
    print(f"get_content_type_counts", query)
    result = get(url, format="json")
    return [create_dict(result["columns"], row) for row in result["rows"]]
