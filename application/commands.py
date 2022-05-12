import datetime
import re

import requests
from flask.cli import AppGroup
from jsonpath import JSONPath

from application.models import TestRun, Result, ResponseData, Assertion, AssertionType

data_test_cli = AppGroup("data-test")

BASE_API_URL = "https://www.digital-land.info/entity.json"


@data_test_cli.command("run")
def run():
    _run_tests()


def _run_tests():
    from application.extensions import db
    from application.data_tests.tests import tests, local_authorities

    print(f"Running tests at {datetime.datetime.utcnow()}")
    results = []
    for la in local_authorities:

        for test, details in tests[la].items():
            print(f"Running test: {test}")

            dataset = details.get("dataset")
            query = details.get("query")
            assertions = details.get("assertions", {})
            warnings = details.get("warnings", {})
            ticket = details.get("ticket")

            checks = {"strict": assertions, "warning": warnings}

            test_url = f"{BASE_API_URL}{query}"
            resp = requests.get(test_url)
            resp.raise_for_status()
            data = resp.json()

            # sort by entity id to give tests a predicable ordering
            if data["count"] > 1 and data.get("entities"):
                data["entities"].sort(key=lambda e: e["entity"])

            response_data = ResponseData(query=query, test_name=test, data=data)
            result = Result(
                query=query,
                organisation=la,
                dataset=dataset,
                test_name=test,
                ticket=ticket,
            )
            response_data.results.append(result)
            results.append(result)

            for level, checks in checks.items():
                for path, expected in checks.items():
                    print(f"path = {path} expect = {expected} : check {level}")
                    parsed = JSONPath(path).parse(data)
                    assertion_type = AssertionType(level)
                    if parsed:
                        actual = str(parsed[0])
                        expected = str(expected)
                        if expected.startswith("~"):
                            match = True if re.match(expected[1:], actual) else False
                        else:
                            match = expected == actual
                        assertion = Assertion(
                            path=path,
                            expected=expected,
                            actual=actual,
                            match=match,
                            assertion_type=assertion_type,
                        )
                    else:
                        assertion = Assertion(
                            path=path,
                            expected=expected,
                            actual=None,
                            match=None,
                            assertion_type=assertion_type,
                        )
                    result.assertions.append(assertion)

            db.session.add(response_data)

    test_run = TestRun(results=results)
    db.session.add(test_run)
    db.session.commit()

    print(f"Finished running tests at {datetime.datetime.utcnow()}")


@data_test_cli.command("delete-old-tests")
def delete_old_tests():
    from application.extensions import db
    from datetime import datetime, timedelta

    now = datetime.now()
    yesterday = now - timedelta(days=1)

    tests_runs_to_delete = (
        db.session.query(TestRun).filter(TestRun.created_timestamp < yesterday).all()
    )

    for t in tests_runs_to_delete:
        print(f"Deleting test from {t.created_timestamp}")
        db.session.delete(t)
    db.session.commit()
