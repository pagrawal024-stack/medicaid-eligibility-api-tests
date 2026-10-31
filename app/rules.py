"""EDBC (Eligibility Determination & Benefit Calculation) rules.

These are SIMPLIFIED training rules modelled loosely on Medicaid. They are not
the policy of any real state and must not be used for real decisions.

Income limits are a percentage of the Federal Poverty Level (FPL), using the
2025 HHS guideline for the 48 contiguous states: $15,650 for one person plus
$5,500 for each additional household member.

All money is handled in integer cents, so boundary values are exact.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

FPL_BASE_DOLLARS = 15650
FPL_PER_ADDITIONAL_DOLLARS = 5500

CATEGORY_FPL_LIMIT_PERCENT = {
    "CHILD": 200,     # under 19
    "PREGNANT": 200,  # pregnant, any age 19+
    "AGED": 100,      # 65 and over
    "ADULT": 138,     # 19-64 expansion adult
}

WORK_HOURS_REQUIRED = 80  # per month, ADULT category only

# Reason codes are always returned in this order.
REASON_ORDER = [
    "NOT_STATE_RESIDENT",
    "CITIZENSHIP_NOT_VERIFIED",
    "INCOME_OVER_LIMIT",
    "WORK_REQUIREMENT_NOT_MET",
]


def annual_fpl_dollars(household_size: int) -> int:
    return FPL_BASE_DOLLARS + FPL_PER_ADDITIONAL_DOLLARS * (household_size - 1)


def age_on(date_of_birth: date, as_of: date) -> int:
    had_birthday = (as_of.month, as_of.day) >= (date_of_birth.month, date_of_birth.day)
    return as_of.year - date_of_birth.year - (0 if had_birthday else 1)


def category_for(age: int, pregnant: bool) -> str:
    if age < 19:
        return "CHILD"
    if pregnant:
        return "PREGNANT"
    if age >= 65:
        return "AGED"
    return "ADULT"


def determine(applicant: dict, application: dict) -> dict:
    """Return the eligibility decision for one application."""
    dob = date.fromisoformat(applicant["date_of_birth"])
    as_of = date.fromisoformat(application["application_date"])
    age = age_on(dob, as_of)
    category = category_for(age, bool(applicant["pregnant"]))
    limit_pct = CATEGORY_FPL_LIMIT_PERCENT[category]

    fpl = annual_fpl_dollars(application["household_size"])
    income_cents = application["monthly_income_cents"]

    # Eligible when annual income <= FPL * limit%.  In cents:
    # income_cents * 12 <= fpl_dollars * 100 * limit_pct / 100
    annual_income_cents = income_cents * 12
    annual_limit_cents = fpl * limit_pct
    monthly_limit_cents = annual_limit_cents // 12

    fpl_percent = (Decimal(annual_income_cents) / Decimal(fpl)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    reasons = []
    if not applicant["state_resident"]:
        reasons.append("NOT_STATE_RESIDENT")
    if not applicant["citizen_or_qualified"]:
        reasons.append("CITIZENSHIP_NOT_VERIFIED")
    if annual_income_cents > annual_limit_cents:
        reasons.append("INCOME_OVER_LIMIT")

    if category != "ADULT":
        work_requirement = "NOT_APPLICABLE"
    elif applicant["disabled"] or applicant["caregiver_child_under_14"]:
        work_requirement = "EXEMPT"
    elif application["work_hours_monthly"] >= WORK_HOURS_REQUIRED:
        work_requirement = "MET"
    else:
        work_requirement = "NOT_MET"
        reasons.append("WORK_REQUIREMENT_NOT_MET")

    reasons.sort(key=REASON_ORDER.index)
    return {
        "status": "DENIED" if reasons else "APPROVED",
        "category": category,
        "age_at_application": age,
        "fpl_percent": f"{fpl_percent:.2f}",
        "income_limit_cents": monthly_limit_cents,
        "work_requirement": work_requirement,
        "reason_codes": reasons,
    }
