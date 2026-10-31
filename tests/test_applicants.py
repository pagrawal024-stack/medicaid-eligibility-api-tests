"""Applicant registration: positive, contract, database and negative tests."""
from datetime import date, timedelta

import pytest

from framework.data_factory import applicant_payload
from framework.schema_validator import assert_matches_schema


@pytest.mark.smoke
def test_create_applicant_returns_201_and_matches_contract(applicants):
    payload = applicant_payload(preferred_language="es")

    response = applicants.create(payload)

    assert response.status_code == 201
    body = response.json()
    assert_matches_schema(body, "applicant")
    for field, value in payload.items():
        assert body[field] == value, f"{field}: sent {value!r}, got {body[field]!r}"


@pytest.mark.db
def test_created_applicant_is_stored_correctly_in_database(applicants, db):
    payload = applicant_payload(pregnant=True, preferred_language="hi", phone=None)

    applicant_id = applicants.create(payload).json()["id"]
    row = db.applicant(applicant_id)

    assert row is not None, "Applicant row missing from database"
    assert row["first_name"] == payload["first_name"]
    assert row["last_name"] == payload["last_name"]
    assert row["date_of_birth"] == payload["date_of_birth"]
    assert row["preferred_language"] == "hi"
    assert row["pregnant"] == 1
    assert row["disabled"] == 0
    assert row["email"] == payload["email"]
    assert row["phone"] is None


@pytest.mark.regression
def test_get_applicant_returns_same_data_as_create(applicants, new_applicant):
    created = new_applicant(preferred_language="zh")

    response = applicants.get(created["id"])

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.regression
def test_get_unknown_applicant_returns_404(applicants):
    response = applicants.get(999_999)

    assert response.status_code == 404
    assert_matches_schema(response.json(), "error")
    assert response.json()["error"] == "NOT_FOUND"


TOMORROW = (date.today() + timedelta(days=1)).isoformat()


@pytest.mark.regression
@pytest.mark.parametrize(
    "overrides, bad_field",
    [
        ({"first_name": ""}, "first_name"),
        ({"first_name": "A" * 51}, "first_name"),
        ({"preferred_language": "fr"}, "preferred_language"),
        ({"date_of_birth": TOMORROW}, "date_of_birth"),
        ({"date_of_birth": "31-12-1990"}, "date_of_birth"),
        ({"email": "not-an-email"}, "email"),
        ({"phone": "12345"}, "phone"),
        ({"state_resident": "yes"}, "state_resident"),
        ({"unexpected_field": 1}, "unexpected_field"),
    ],
    ids=["empty_first_name", "first_name_too_long", "unsupported_language", "dob_in_future",
         "dob_wrong_format", "invalid_email", "phone_too_short", "boolean_as_string",
         "unknown_field"],
)
def test_invalid_applicant_is_rejected_with_field_error(applicants, overrides, bad_field):
    payload = applicant_payload(**overrides)

    response = applicants.create(payload)

    assert response.status_code == 422
    body = response.json()
    assert_matches_schema(body, "error")
    assert body["error"] == "VALIDATION_ERROR"
    assert bad_field in [d["field"] for d in body["details"]], body["details"]


@pytest.mark.regression
def test_missing_required_field_is_rejected(applicants):
    payload = applicant_payload()
    del payload["date_of_birth"]

    response = applicants.create(payload)

    assert response.status_code == 422
    assert "date_of_birth" in [d["field"] for d in response.json()["details"]]


@pytest.mark.regression
def test_applicant_without_any_contact_method_is_rejected(applicants):
    response = applicants.create(applicant_payload(email=None, phone=None))

    assert response.status_code == 422
    messages = " ".join(d["message"] for d in response.json()["details"])
    assert "email or phone" in messages


@pytest.mark.regression
def test_non_json_body_returns_400(client):
    response = client.post("/api/v1/applicants", data="not json",
                           headers={"Content-Type": "text/plain"})

    assert response.status_code == 400
    assert response.json()["error"] == "BAD_REQUEST"
