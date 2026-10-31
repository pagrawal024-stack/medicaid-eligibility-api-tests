"""End-to-end member journey: register -> apply -> determine -> notify."""
import pytest

from framework.data_factory import applicant_payload, application_payload


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.db
def test_spanish_speaking_parent_is_approved_and_notified(applicants, applications, db):
    # 1. Register a caregiver who prefers Spanish
    payload = applicant_payload(date_of_birth="1992-03-10", caregiver_child_under_14=True,
                                preferred_language="es")
    reg = applicants.create(payload)
    assert reg.status_code == 201
    applicant_id = reg.json()["id"]

    # 2. Apply: household of 3, $3,000/month, not working (exempt as caregiver)
    app_resp = applications.create(application_payload(
        applicant_id, household_size=3, monthly_income=3000.00, work_hours_monthly=0))
    assert app_resp.status_code == 201
    application_id = app_resp.json()["id"]
    assert db.application(application_id)["status"] == "PENDING"

    # 3. Run eligibility
    det = applications.determine(application_id)
    assert det.status_code == 201
    decision = det.json()
    assert decision["status"] == "APPROVED"
    assert decision["category"] == "ADULT"
    assert decision["work_requirement"] == "EXEMPT"
    assert decision["age_at_application"] == 34

    # 4. Application record reflects the decision
    final = applications.get(application_id).json()
    assert final["status"] == "APPROVED"
    assert db.application(application_id)["status"] == "APPROVED"

    # 5. Spanish approval notice on both channels
    notices = applications.notices(application_id).json()
    assert {n["channel"] for n in notices} == {"EMAIL", "SMS"}
    assert all(n["language"] == "es" for n in notices)
    assert all(n["template_code"] == "APPROVAL_NOTICE" for n in notices)
    assert len(db.notices(application_id)) == 2
