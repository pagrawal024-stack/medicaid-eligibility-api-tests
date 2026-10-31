"""Application intake: contract, money precision in the database, negative tests."""
import pytest

from framework.data_factory import application_payload
from framework.schema_validator import assert_matches_schema


@pytest.mark.smoke
def test_create_application_starts_pending(applications, new_applicant):
    applicant = new_applicant()

    response = applications.create(application_payload(applicant["id"], household_size=3))

    assert response.status_code == 201
    body = response.json()
    assert_matches_schema(body, "application")
    assert body["status"] == "PENDING"
    assert body["determination"] is None
    assert body["household_size"] == 3


@pytest.mark.db
@pytest.mark.parametrize("income, expected_cents",
                         [(0, 0), (0.01, 1), (1799.76, 179976), (123456.78, 12345678)])
def test_income_is_stored_in_exact_cents(new_applicant, new_application, db, income, expected_cents):
    """Floating-point money is a classic defect source; the DB must hold exact cents."""
    applicant = new_applicant()

    application = new_application(applicant["id"], monthly_income=income)
    row = db.application(application["id"])

    assert row["monthly_income_cents"] == expected_cents
    assert row["status"] == "PENDING"
    assert row["applicant_id"] == applicant["id"]


@pytest.mark.regression
def test_application_for_unknown_applicant_returns_404(applications):
    response = applications.create(application_payload(applicant_id=999_999))

    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


@pytest.mark.regression
@pytest.mark.parametrize(
    "overrides, bad_field",
    [
        ({"household_size": 0}, "household_size"),
        ({"household_size": 21}, "household_size"),
        ({"monthly_income": -0.01}, "monthly_income"),
        ({"monthly_income": 10.123}, "monthly_income"),
        ({"monthly_income": "abc"}, "monthly_income"),
        ({"work_hours_monthly": -1}, "work_hours_monthly"),
        ({"work_hours_monthly": 745}, "work_hours_monthly"),
        ({"application_date": "2026-02-30"}, "application_date"),
    ],
    ids=["household_zero", "household_too_large", "negative_income", "three_decimal_income",
         "income_not_number", "negative_hours", "hours_more_than_month", "impossible_date"],
)
def test_invalid_application_is_rejected(applications, new_applicant, overrides, bad_field):
    applicant = new_applicant()

    response = applications.create(application_payload(applicant["id"], **overrides))

    assert response.status_code == 422
    assert bad_field in [d["field"] for d in response.json()["details"]]


@pytest.mark.regression
@pytest.mark.parametrize("household_size, hours", [(1, 0), (20, 744)],
                         ids=["minimums", "maximums"])
def test_boundary_values_are_accepted(applications, new_applicant, household_size, hours):
    applicant = new_applicant()

    response = applications.create(application_payload(
        applicant["id"], household_size=household_size, work_hours_monthly=hours))

    assert response.status_code == 201


@pytest.mark.regression
def test_get_unknown_application_returns_404(applications):
    assert applications.get(999_999).status_code == 404
