"""Builds valid request payloads; tests override only the fields they care about."""
import uuid
from datetime import date


def dob_for_age(age: int, as_of: date) -> str:
    """Date of birth that makes someone exactly `age` on `as_of` (their birthday)."""
    try:
        return as_of.replace(year=as_of.year - age).isoformat()
    except ValueError:  # 29 Feb on a non-leap year
        return as_of.replace(year=as_of.year - age, day=28).isoformat()


def applicant_payload(**overrides) -> dict:
    unique = uuid.uuid4().hex[:8]
    payload = {
        "first_name": "Test",
        "last_name": f"Member{unique}",
        "date_of_birth": "1990-01-15",
        "state_resident": True,
        "citizen_or_qualified": True,
        "pregnant": False,
        "disabled": False,
        "caregiver_child_under_14": False,
        "preferred_language": "en",
        "email": f"member.{unique}@example.com",
        "phone": "+15550100001",
    }
    payload.update(overrides)
    return payload


def application_payload(applicant_id: int, **overrides) -> dict:
    payload = {
        "applicant_id": applicant_id,
        "household_size": 1,
        "monthly_income": 1000.00,
        "work_hours_monthly": 80,
        "application_date": "2026-07-01",
    }
    payload.update(overrides)
    return payload
