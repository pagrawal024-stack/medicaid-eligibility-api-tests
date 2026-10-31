"""Mock Medicaid eligibility REST API (Flask + SQLite).

Run:  python -m app.main            (defaults to http://127.0.0.1:8000)
Env:  PORT, DB_PATH, API_CLIENT_ID, API_CLIENT_SECRET
"""
import os
import secrets
from functools import wraps

from flask import Flask, g, jsonify, request
from pydantic import ValidationError

from app import db, rules
from app.notices import build_notices
from app.schemas import ApplicantCreate, ApplicationCreate

app = Flask(__name__)
app.json.ensure_ascii = False  # return Hindi/Chinese text as-is

CLIENT_ID = os.getenv("API_CLIENT_ID", "qa-client")
CLIENT_SECRET = os.getenv("API_CLIENT_SECRET", "qa-secret")
_TOKENS: set[str] = set()


# ---------- helpers ----------

def error(status: int, code: str, message: str, details=None):
    body = {"error": code, "message": message}
    if details is not None:
        body["details"] = details
    return jsonify(body), status


def validation_error(exc: ValidationError):
    details = [
        {"field": ".".join(str(p) for p in e["loc"]) or "body", "message": e["msg"]}
        for e in exc.errors()
    ]
    return error(422, "VALIDATION_ERROR", "Request body is invalid", details)


def require_token(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or header[7:] not in _TOKENS:
            return error(401, "UNAUTHORIZED", "A valid bearer token is required")
        return view(*args, **kwargs)
    return wrapper


def json_body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


@app.before_request
def open_db():
    g.conn = db.get_conn()


@app.teardown_request
def close_db(_exc):
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


def applicant_out(row) -> dict:
    d = dict(row)
    for k in ("state_resident", "citizen_or_qualified", "pregnant", "disabled",
              "caregiver_child_under_14"):
        d[k] = bool(d[k])
    return d


def determination_out(row) -> dict | None:
    if row is None:
        return None
    return {
        "status": row["status"],
        "category": row["category"],
        "fpl_percent": row["fpl_percent"],
        "monthly_income_limit": row["income_limit_cents"] / 100,
        "work_requirement": row["work_requirement"],
        "reason_codes": [c for c in row["reason_codes"].split(",") if c],
        "determined_at": row["determined_at"],
    }


def application_out(row, det_row=None) -> dict:
    return {
        "id": row["id"],
        "applicant_id": row["applicant_id"],
        "household_size": row["household_size"],
        "monthly_income": row["monthly_income_cents"] / 100,
        "work_hours_monthly": row["work_hours_monthly"],
        "application_date": row["application_date"],
        "status": row["status"],
        "determination": determination_out(det_row),
    }


# ---------- endpoints ----------

@app.get("/health")
def health():
    return jsonify({"status": "UP"})


@app.post("/auth/token")
def issue_token():
    body = json_body() or {}
    if body.get("client_id") != CLIENT_ID or body.get("client_secret") != CLIENT_SECRET:
        return error(401, "INVALID_CLIENT", "client_id or client_secret is wrong")
    token = secrets.token_hex(24)
    _TOKENS.add(token)
    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 3600})


@app.post("/api/v1/applicants")
@require_token
def create_applicant():
    body = json_body()
    if body is None:
        return error(400, "BAD_REQUEST", "Body must be a JSON object")
    try:
        data = ApplicantCreate.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    cur = g.conn.execute(
        """INSERT INTO applicants (first_name, last_name, date_of_birth, state_resident,
               citizen_or_qualified, pregnant, disabled, caregiver_child_under_14,
               preferred_language, email, phone)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (data.first_name, data.last_name, data.date_of_birth.isoformat(),
         int(data.state_resident), int(data.citizen_or_qualified), int(data.pregnant),
         int(data.disabled), int(data.caregiver_child_under_14),
         data.preferred_language, data.email, data.phone),
    )
    g.conn.commit()
    row = g.conn.execute("SELECT * FROM applicants WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(applicant_out(row)), 201


@app.get("/api/v1/applicants/<int:applicant_id>")
@require_token
def get_applicant(applicant_id: int):
    row = g.conn.execute("SELECT * FROM applicants WHERE id = ?", (applicant_id,)).fetchone()
    if row is None:
        return error(404, "NOT_FOUND", f"Applicant {applicant_id} not found")
    return jsonify(applicant_out(row))


@app.post("/api/v1/applications")
@require_token
def create_application():
    body = json_body()
    if body is None:
        return error(400, "BAD_REQUEST", "Body must be a JSON object")
    try:
        data = ApplicationCreate.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    exists = g.conn.execute("SELECT 1 FROM applicants WHERE id = ?", (data.applicant_id,)).fetchone()
    if exists is None:
        return error(404, "NOT_FOUND", f"Applicant {data.applicant_id} not found")

    income_cents = int(data.monthly_income * 100)
    cur = g.conn.execute(
        """INSERT INTO applications (applicant_id, household_size, monthly_income_cents,
               work_hours_monthly, application_date)
           VALUES (?,?,?,?,?)""",
        (data.applicant_id, data.household_size, income_cents,
         data.work_hours_monthly, data.application_date.isoformat()),
    )
    g.conn.commit()
    row = g.conn.execute("SELECT * FROM applications WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(application_out(row)), 201


@app.get("/api/v1/applications/<int:application_id>")
@require_token
def get_application(application_id: int):
    row = g.conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    if row is None:
        return error(404, "NOT_FOUND", f"Application {application_id} not found")
    det = g.conn.execute(
        "SELECT * FROM determinations WHERE application_id = ?", (application_id,)
    ).fetchone()
    return jsonify(application_out(row, det))


@app.post("/api/v1/applications/<int:application_id>/determination")
@require_token
def run_determination(application_id: int):
    appl = g.conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    if appl is None:
        return error(404, "NOT_FOUND", f"Application {application_id} not found")
    if appl["status"] != "PENDING":
        return error(409, "ALREADY_DETERMINED", f"Application {application_id} is already {appl['status']}")

    applicant = dict(g.conn.execute(
        "SELECT * FROM applicants WHERE id = ?", (appl["applicant_id"],)
    ).fetchone())
    decision = rules.determine(applicant, dict(appl))

    g.conn.execute(
        """INSERT INTO determinations (application_id, status, category, fpl_percent,
               income_limit_cents, work_requirement, reason_codes)
           VALUES (?,?,?,?,?,?,?)""",
        (application_id, decision["status"], decision["category"], decision["fpl_percent"],
         decision["income_limit_cents"], decision["work_requirement"],
         ",".join(decision["reason_codes"])),
    )
    g.conn.execute("UPDATE applications SET status = ? WHERE id = ?",
                   (decision["status"], application_id))
    for n in build_notices(applicant, decision["status"]):
        g.conn.execute(
            """INSERT INTO notices (application_id, template_code, language, channel,
                   recipient, subject) VALUES (?,?,?,?,?,?)""",
            (application_id, n["template_code"], n["language"], n["channel"],
             n["recipient"], n["subject"]),
        )
    g.conn.commit()

    det = g.conn.execute(
        "SELECT * FROM determinations WHERE application_id = ?", (application_id,)
    ).fetchone()
    body = determination_out(det)
    body["application_id"] = application_id
    body["age_at_application"] = decision["age_at_application"]
    return jsonify(body), 201


@app.get("/api/v1/applications/<int:application_id>/notices")
@require_token
def list_notices(application_id: int):
    if g.conn.execute("SELECT 1 FROM applications WHERE id = ?", (application_id,)).fetchone() is None:
        return error(404, "NOT_FOUND", f"Application {application_id} not found")
    rows = g.conn.execute(
        "SELECT * FROM notices WHERE application_id = ? ORDER BY id", (application_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


db.init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)
