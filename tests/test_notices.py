"""Multilingual member notices (email and SMS) sent after a determination."""
import pytest

from framework.schema_validator import assert_matches_schema
from tests.conftest import load_json

SUBJECTS = load_json("notice_subjects.json")
LANGUAGES = ["en", "es", "hi", "zh"]

APPROVED = {"monthly_income": 1000.00, "work_hours_monthly": 80}
DENIED = {"monthly_income": 9000.00, "work_hours_monthly": 80}


def _determine(new_applicant, new_application, applications, applicant_kw, application_kw):
    applicant = new_applicant(**applicant_kw)
    application = new_application(applicant["id"], **application_kw)
    assert applications.determine(application["id"]).status_code == 201
    return applicant, application


@pytest.mark.regression
@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("outcome, template", [(APPROVED, "APPROVAL_NOTICE"),
                                               (DENIED, "DENIAL_NOTICE")],
                         ids=["approved", "denied"])
def test_notice_is_sent_in_preferred_language(new_applicant, new_application, applications,
                                              language, outcome, template):
    _, application = _determine(new_applicant, new_application, applications,
                                {"preferred_language": language}, outcome)

    response = applications.notices(application["id"])

    assert response.status_code == 200
    notices = response.json()
    assert_matches_schema(notices, "notice_list")
    assert notices, "No notices were generated"
    for notice in notices:
        assert notice["template_code"] == template
        assert notice["language"] == language
        assert notice["subject"] == SUBJECTS[template][language]


@pytest.mark.regression
@pytest.mark.db
@pytest.mark.parametrize(
    "contact, expected_channels",
    [
        ({"email": "only.email@example.com", "phone": None}, {"EMAIL": "only.email@example.com"}),
        ({"email": None, "phone": "+15550100002"}, {"SMS": "+15550100002"}),
        ({"email": "both@example.com", "phone": "+15550100003"},
         {"EMAIL": "both@example.com", "SMS": "+15550100003"}),
    ],
    ids=["email_only", "sms_only", "email_and_sms"],
)
def test_notice_goes_to_every_contact_channel(new_applicant, new_application, applications, db,
                                              contact, expected_channels):
    _, application = _determine(new_applicant, new_application, applications, contact, APPROVED)

    api_channels = {n["channel"]: n["recipient"] for n in applications.notices(application["id"]).json()}
    db_channels = {n["channel"]: n["recipient"] for n in db.notices(application["id"])}

    assert api_channels == expected_channels
    assert db_channels == expected_channels


@pytest.mark.regression
@pytest.mark.db
def test_no_notice_before_determination(new_applicant, new_application, applications, db):
    applicant = new_applicant()
    application = new_application(applicant["id"])

    assert applications.notices(application["id"]).json() == []
    assert db.notices(application["id"]) == []


@pytest.mark.db
def test_database_has_no_orphan_notices(db):
    """Data-integrity check across the whole run: every notice has a determination."""
    assert db.orphan_notices() == 0
