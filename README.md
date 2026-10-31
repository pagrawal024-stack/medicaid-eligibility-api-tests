# Medicaid Eligibility API – Test Automation Framework

![API Tests](https://github.com/pagrawal024-stack/medicaid-eligibility-api-tests/actions/workflows/api-tests.yml/badge.svg)

A Python + Pytest automation framework for a REST API that decides Medicaid eligibility
(EDBC – Eligibility Determination & Benefit Calculation) and sends multilingual notices.

Every business rule is validated at **two layers**: the API response *and* the database
record behind it, the way eligibility systems are tested in practice.

> The API in `app/` is a small mock built for this project. Its rules are a **simplified
> training model** inspired by Medicaid, not the policy of any real state.

---

## What this project demonstrates

| Area | How |
|---|---|
| API automation | `requests` with a reusable client and a service layer (one class per resource) |
| Backend data validation | Read-only SQL queries compare every determination, application and notice with the API |
| Data-driven testing | 19 eligibility scenarios live in JSON; adding a case needs no code change |
| Boundary value analysis | Income exactly at the limit vs one cent over, 19th and 65th birthdays, 79 vs 80 work hours |
| Contract testing | JSON Schema validation of every response type |
| Negative testing | Auth failures, 20 invalid-input cases, 404 and 409 handling |
| Localization testing | Approval and denial notices in English, Spanish, Hindi and Chinese |
| CI/CD | GitHub Actions: smoke gate, then regression on Python 3.11–3.13, nightly run, HTML + JUnit reports |
| Isolation | Each run starts its own API on a free port with a fresh database |

**77 tests** · smoke 5 · regression 66 · database 31 · end-to-end 1 · runtime ≈ 2 s

---

## Business rules under test

| Category | Who | Income limit | Work requirement |
|---|---|---|---|
| CHILD | Under 19 | 200% FPL | Not applicable |
| PREGNANT | Pregnant, 19+ | 200% FPL | Not applicable |
| ADULT | 19–64 | 138% FPL | 80 hrs/month unless disabled or caregiver of a child under 14 |
| AGED | 65+ | 100% FPL | Not applicable |

- FPL uses the 2025 HHS guideline: $15,650 for one person + $5,500 per extra member.
- An applicant must also be a state resident and a citizen or qualified non-citizen.
- A denial lists **every** reason, in a fixed order: `NOT_STATE_RESIDENT`,
  `CITIZENSHIP_NOT_VERIFIED`, `INCOME_OVER_LIMIT`, `WORK_REQUIREMENT_NOT_MET`.
- Money is stored as integer cents, so boundaries are exact.

---

## Project structure

```
├── app/                         # Mock API under test (Flask + SQLite)
│   ├── main.py                  #   REST endpoints and token auth
│   ├── rules.py                 #   EDBC eligibility rules
│   ├── notices.py               #   Multilingual notice templates
│   ├── schemas.py               #   Request validation
│   └── db.py                    #   Database schema
├── framework/                   # Reusable test framework
│   ├── api_client.py            #   HTTP client: session, auth, timeout, request logging
│   ├── services/                #   One service object per API resource
│   ├── db_validator.py          #   Read-only SQL validation helpers
│   ├── schema_validator.py      #   JSON Schema assertions
│   ├── schemas/                 #   API contracts
│   ├── data_factory.py          #   Test-data builders
│   └── config.py                #   Environment-based configuration
├── tests/
│   ├── conftest.py              #   Fixtures: starts the API, auth token, DB access
│   ├── data/                    #   Eligibility scenarios and expected notice text
│   ├── test_auth.py
│   ├── test_applicants.py
│   ├── test_applications.py
│   ├── test_eligibility_rules.py
│   ├── test_notices.py
│   └── test_end_to_end.py
├── .github/workflows/api-tests.yml
├── pytest.ini
└── requirements.txt
```

---

## Run it

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest                             # everything
pytest -m smoke                    # quick health check
pytest -m db                       # only database-validation tests
pytest -k one_cent_over            # one scenario by name
pytest --html=reports/report.html --self-contained-html   # HTML report
pytest --log-cli-level=INFO        # print every request and response
```

The suite starts the API itself. To test an API that is already running:

```bash
python -m app.main                                  # terminal 1 (port 8000)
BASE_URL=http://127.0.0.1:8000 DB_PATH=eligibility.db pytest   # terminal 2
```

### Try the API by hand

```bash
python -m app.main
curl -X POST localhost:8000/auth/token -H "Content-Type: application/json" \
     -d '{"client_id":"qa-client","client_secret":"qa-secret"}'
```

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| POST | `/auth/token` | Get a bearer token |
| POST / GET | `/api/v1/applicants`, `/api/v1/applicants/{id}` | Register / read a member |
| POST / GET | `/api/v1/applications`, `/api/v1/applications/{id}` | Submit / read an application |
| POST | `/api/v1/applications/{id}/determination` | Run eligibility (once only, else 409) |
| GET | `/api/v1/applications/{id}/notices` | Notices sent to the member |

---

## Adding a test scenario

Add an entry to `tests/data/eligibility_cases.json`:

```json
{
  "id": "adult_hh2_just_under_limit",
  "applicant": {"age": 45},
  "application": {"household_size": 2, "monthly_income": 2432.25, "work_hours_monthly": 80},
  "expected": {"status": "APPROVED", "category": "ADULT", "monthly_income_limit": 2432.25,
               "fpl_percent": "138.00", "work_requirement": "MET", "reason_codes": []}
}
```

It runs as its own test case, checked against both the API and the database.

---

## Design notes

- **Tests prove they can fail.** During development, three bugs were planted in the API
  (an off-by-one at the income limit, 19-year-olds treated as children, and a changed
  Spanish template). The suite caught each one.
- **Display rounding vs eligibility.** $1,799.76 for one person shows as 138.00% FPL but is
  still one cent over the limit and must be denied. A test guards that edge.
- **The database is read-only to tests.** `DbValidator` opens SQLite with `mode=ro`, so a test
  can never "fix" data behind the API's back.
- **No duplicate notices.** Re-running a determination returns 409 and the test confirms
  exactly one determination and one notice per channel exist.
