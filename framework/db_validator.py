"""Backend data validation: query the database directly and compare it with
what the API returned. Read-only by design (the connection is opened with
mode=ro), so tests can never change data behind the API's back.
"""
import sqlite3


class DbValidator:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self._query(sql, params)
        assert len(rows) <= 1, f"Expected at most one row, got {len(rows)}"
        return rows[0] if rows else None

    def applicant(self, applicant_id: int) -> dict | None:
        return self._one("SELECT * FROM applicants WHERE id = ?", (applicant_id,))

    def application(self, application_id: int) -> dict | None:
        return self._one("SELECT * FROM applications WHERE id = ?", (application_id,))

    def determination(self, application_id: int) -> dict | None:
        return self._one("SELECT * FROM determinations WHERE application_id = ?", (application_id,))

    def determination_count(self, application_id: int) -> int:
        return self._one(
            "SELECT COUNT(*) AS n FROM determinations WHERE application_id = ?", (application_id,)
        )["n"]

    def notices(self, application_id: int) -> list[dict]:
        return self._query(
            "SELECT * FROM notices WHERE application_id = ? ORDER BY id", (application_id,)
        )

    def orphan_notices(self) -> int:
        """Notices whose application has no determination -- should always be 0."""
        return self._one(
            """SELECT COUNT(*) AS n FROM notices n
               LEFT JOIN determinations d ON d.application_id = n.application_id
               WHERE d.id IS NULL"""
        )["n"]
