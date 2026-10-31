"""EDBC rules, data-driven from tests/data/eligibility_cases.json.

Each case is checked twice: once on the API response and once directly in the
database, the same way you would validate a real eligibility system with SQL.
To add a scenario, add a JSON entry -- no code change needed.
"""
from datetime import date

import pytest

from framework.data_factory import dob_for_age
from framework.schema_validator import assert_matches_schema
from tests.conftest import load_json

APPLICATION_DATE = "2026-07-01"
CASES = load_json("eligibility_cases.json")


def _applicant_overrides(spec: dict) -> dict:
    spec = dict(spec)
    if "age" in spec:
        spec["date_of_birth"] = dob_for_age(spec.pop("age"), date.fromisoformat(APPLICATION_DATE))
    return spec


@pytest.mark.regression
@pytest.mark.db
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_eligibility_determination(case, new_applicant, new_application, applications, db):
    expected = case["expected"]
    applicant = new_applicant(**_applicant_overrides(case["applicant"]))
    application = new_application(
        applicant["id"], application_date=APPLICATION_DATE, **case["application"])

    response = applications.determine(application["id"])

    # --- API layer ---
    assert response.status_code == 201, response.text
    body = response.json()
    assert_matches_schema(body, "determination")
    assert body["status"] == expected["status"]
    assert body["category"] == expected["category"]
    assert body["fpl_percent"] == expected["fpl_percent"]
    assert body["monthly_income_limit"] == expected["monthly_income_limit"]
    assert body["work_requirement"] == expected["work_requirement"]
    assert body["reason_codes"] == expected["reason_codes"]

    # --- Database layer ---
    det = db.determination(application["id"])
    assert det is not None, "No determination row written"
    assert det["status"] == expected["status"]
    assert det["category"] == expected["category"]
    assert det["income_limit_cents"] == round(expected["monthly_income_limit"] * 100)
    assert det["reason_codes"] == ",".join(expected["reason_codes"])
    assert db.application(application["id"])["status"] == expected["status"]


@pytest.mark.regression
@pytest.mark.db
def test_determination_cannot_run_twice(new_applicant, new_application, applications, db):
    applicant = new_applicant()
    application = new_application(applicant["id"])
    assert applications.determine(application["id"]).status_code == 201

    second = applications.determine(application["id"])

    assert second.status_code == 409
    assert second.json()["error"] == "ALREADY_DETERMINED"
    assert db.determination_count(application["id"]) == 1
    assert len(db.notices(application["id"])) == 2, "Duplicate notices were sent"


@pytest.mark.regression
def test_determination_for_unknown_application_returns_404(applications):
    assert applications.determine(999_999).status_code == 404


@pytest.mark.regression
def test_get_application_includes_determination(new_applicant, new_application, applications):
    applicant = new_applicant()
    application = new_application(applicant["id"])
    determined = applications.determine(application["id"]).json()

    body = applications.get(application["id"]).json()

    assert_matches_schema(body, "application")
    assert body["status"] == determined["status"]
    assert body["determination"]["category"] == determined["category"]
    assert body["determination"]["reason_codes"] == determined["reason_codes"]
