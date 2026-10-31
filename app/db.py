"""SQLite persistence for the mock eligibility system."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS applicants (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name               TEXT    NOT NULL,
    last_name                TEXT    NOT NULL,
    date_of_birth            TEXT    NOT NULL,
    state_resident           INTEGER NOT NULL,
    citizen_or_qualified     INTEGER NOT NULL,
    pregnant                 INTEGER NOT NULL DEFAULT 0,
    disabled                 INTEGER NOT NULL DEFAULT 0,
    caregiver_child_under_14 INTEGER NOT NULL DEFAULT 0,
    preferred_language       TEXT    NOT NULL,
    email                    TEXT,
    phone                    TEXT,
    created_at               TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_id         INTEGER NOT NULL REFERENCES applicants(id),
    household_size       INTEGER NOT NULL,
    monthly_income_cents INTEGER NOT NULL,
    work_hours_monthly   INTEGER NOT NULL,
    application_date     TEXT    NOT NULL,
    status               TEXT    NOT NULL DEFAULT 'PENDING',
    created_at           TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS determinations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id     INTEGER NOT NULL UNIQUE REFERENCES applications(id),
    status             TEXT    NOT NULL,
    category           TEXT    NOT NULL,
    fpl_percent        TEXT    NOT NULL,
    income_limit_cents INTEGER NOT NULL,
    work_requirement   TEXT    NOT NULL,
    reason_codes       TEXT    NOT NULL DEFAULT '',
    determined_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notices (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    template_code  TEXT    NOT NULL,
    language       TEXT    NOT NULL,
    channel        TEXT    NOT NULL,
    recipient      TEXT    NOT NULL,
    subject        TEXT    NOT NULL,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def db_path() -> str:
    return os.getenv("DB_PATH", "eligibility.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
