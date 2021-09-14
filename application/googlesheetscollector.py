import csv
import requests


class GooglesheetsCollector:
    def __init__(
        self, key="1Euj1Hok-gggrOyZFbaRl7A7Ck7bL6koYTGiuOMHjRF8", sheet="performance"
    ) -> None:
        self.sheet = sheet
        self.key = key
        self.main_url = self.generate_csv_url()
        self.session = requests.Session()
        print("SHEET: ", sheet)

    def generate_csv_url(self):
        return (
            "https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&sheet=%s"
            % (self.key, self.sheet)
        )

    def change_sheet(self, sheet):
        self.sheet = sheet
        self.main_url = self.generate_csv_url()

    def read_sheet(self):
        content = self.session.get(self.main_url)
        return content.content.decode("utf-8")

    def read_by_row(self, func=None):
        content = self.read_sheet()
        rows = []
        for row in csv.DictReader(content.splitlines()):
            rows.append(row)
            if func is not None:
                func(row)
        if func is None:
            return rows


def get_datasets():
    sheets_collector = GooglesheetsCollector()
    return sheets_collector.read_by_row()


def get_bfl():
    collector = GooglesheetsCollector(sheet="brownfield-land-by-org")
    rows = collector.read_by_row()

    expected = [o for o in rows if o["expected-to-publish"] == "yes"]
    print("Number of organisations", len(expected))
    additional = [o for o in rows if o["expected-to-publish"] != "yes"]
    noresource = [o for o in expected if o["active-resource"] == "0"]
    withresource = [o for o in expected if int(o["active-resource"]) >= 1]
    return withresource, additional, noresource


def get_organisations():
    collector = GooglesheetsCollector(sheet="organisations")
    return collector.read_by_row()


def get_esk_datasets():
    collector = GooglesheetsCollector(sheet="east-suffolk")
    datasets = collector.read_by_row()
    return [d for d in datasets if d["expected-to-publish"] == "yes"]


def remove_item(l, item):
    if item in l:
        l.remove(item)
    return l


def get_resource_source_stats():
    stats = {"sources": [], "resources": [], "months": []}
    collector = GooglesheetsCollector(sheet="source-by-month-start")
    data = collector.read_by_row()
    months = data[0].keys()

    for month in months:
        if not month in ["pipeline", "name", ""]:
            count = sum([int(d[month]) for d in data if d[month] != ""])
            stats["sources"].append((month, count))

    collector.change_sheet("resource-by-month-start")
    d2 = collector.read_by_row()
    months = d2[0].keys()

    for month in months:
        if not month in ["pipeline", "name", ""]:
            count = sum([int(d[month]) for d in d2 if d[month] != ""])
            stats["resources"].append((month, count))

    months = list(months)
    months = remove_item(months, "pipeline")
    months = remove_item(months, "name")
    months = remove_item(months, "")
    stats["months"] = months

    return stats


def get_org_count():
    collector = GooglesheetsCollector(sheet="organisation-count")
    data = collector.read_by_row()
    # only interested in first row
    return data[0]


def flatten(t, unique=False):
    if unique:
        return set([item for sublist in t for item in sublist])
    return [item for sublist in t for item in sublist]


def get_publishing_orgs():
    collector = GooglesheetsCollector(sheet="organisation-count")
    data = collector.read_by_row()
    publishers = [r["Unique list of orgs"].split(";") for r in data]
    publishers = flatten(publishers, True)
    # remove stray blank publisher id
    if "" in publishers:
        publishers.remove("")

    collector.change_sheet("organisations")
    orgs = collector.read_by_row()

    k_orgs = {}
    for org in orgs:
        k_orgs.setdefault(org["organisation"], {"organisation": []})
        k_orgs[org["organisation"]]["organisation"].append(org)

    for row in data:
        for org in row["Unique list of orgs"].split(";"):
            if org and k_orgs.get(org):
                k_orgs[org].setdefault("resources", {})
                k_orgs[org]["resources"].setdefault("total", 0)
                k_orgs[org]["resources"].setdefault("active", 0)
                k_orgs[org]["resources"]["total"] = k_orgs[org]["resources"][
                    "total"
                ] + int(row["Total resources"])
                k_orgs[org]["resources"]["active"] = k_orgs[org]["resources"][
                    "active"
                ] + int(row["Active resources"])
            else:
                print("no matching key", org)
    return publishers, k_orgs
