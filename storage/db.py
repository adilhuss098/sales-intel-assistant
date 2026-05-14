import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "history.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                person_name TEXT,
                company_name TEXT,
                input_linkedin TEXT,
                input_company TEXT,
                input_context TEXT,
                seller_context TEXT,
                enriched_data TEXT,
                brief_json TEXT NOT NULL,
                confidence_level TEXT
            )
        """)
        conn.commit()


def save_brief(
    person_name: str,
    company_name: str,
    inputs: dict,
    enriched_data: dict,
    brief: dict,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO briefs
              (created_at, person_name, company_name, input_linkedin, input_company,
               input_context, seller_context, enriched_data, brief_json, confidence_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                person_name,
                company_name,
                inputs.get("linkedin", ""),
                inputs.get("company", ""),
                inputs.get("context", ""),
                inputs.get("seller_context", ""),
                json.dumps(enriched_data),
                json.dumps(brief),
                brief.get("confidence_level", ""),
            ),
        )
        conn.commit()
        return cur.lastrowid


def list_briefs(limit: int = 50) -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, created_at, person_name, company_name, confidence_level "
            "FROM briefs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_brief(brief_id: int) -> dict | None:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM briefs WHERE id = ?", (brief_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["enriched_data"] = json.loads(d["enriched_data"] or "{}")
    d["brief_json"] = json.loads(d["brief_json"])
    return d


def delete_brief(brief_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM briefs WHERE id = ?", (brief_id,))
        conn.commit()
