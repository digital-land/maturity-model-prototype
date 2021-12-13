import logging
import urllib.parse

from application.caching import get

logger = logging.getLogger(__name__)

DATASETTE_URL = "http://awseb-awseb-sfpz2cyvurbh-164392685.eu-west-2.elb.amazonaws.com"


def fetch_organisation_entity_number(organisation):
    datasette_url = DATASETTE_URL
    organisation_id = organisation.split(":")
    query_lines = [
        "SELECT",
        "*",
        "FROM",
        "entity",
        "WHERE",
        f"prefix = '{organisation_id[0]}'",
        f"and reference = '{organisation_id[1]}'",
    ]

    query_str = " ".join(query_lines)
    query = urllib.parse.quote(query_str)
    url = f"{datasette_url}/entity.json?sql={query}"
    logger.info("get_organisation_entity_number: %s", url)
    result = get(url, format="json")
    if len(result["rows"]):
        return result["rows"][0][2]
    return None


def fetch_entity_count(dataset=None, organisation_entity=None):
    datasette_url = DATASETTE_URL
    query_lines = [
        "SELECT",
        "dataset,",
        "COUNT(DISTINCT entity) AS count",
        "FROM",
        "entity",
    ]
    if organisation_entity:
        query_lines.append("WHERE")
        query_lines.append(f"organisation_entity = '{organisation_entity}'")
    if dataset:
        if "WHERE" not in query_lines:
            query_lines.append("WHERE")
        else:
            query_lines.append("AND")
        query_lines.append(f"dataset = '{dataset}'")
    else:
        query_lines.append("GROUP BY")
        query_lines.append("dataset")

    query_str = " ".join(query_lines)
    query = urllib.parse.quote(query_str)
    url = f"{datasette_url}/entity.json?sql={query}"
    logger.info("get_entity_count: %s", url)
    result = get(url, format="json")
    if len(result["rows"]):
        return {dataset[0]: dataset[1] for dataset in result["rows"]}
    return {}


def fetch_organisation_entity_count(organisation, dataset=None):
    return fetch_entity_count(
        dataset=dataset,
        organisation_entity=fetch_organisation_entity_number(organisation),
    )
