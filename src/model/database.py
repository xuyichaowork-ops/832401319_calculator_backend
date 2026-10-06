"""SQLite persistence layer for the calculator's calculation history.

Table ``calculation_history``:
    id          INTEGER PRIMARY KEY AUTOINCREMENT
    expression  TEXT    -- the user expression sent by the front end
    result      TEXT    -- the computed result (string form)
    created_at  TEXT    -- local timestamp "YYYY-MM-DD HH:MM:SS"

The database file path can be overridden with the ``CALC_DB`` environment
variable (useful for tests and for deployment isolation).
"""

import os
import sqlite3
from datetime import datetime

_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "..", "calculator.db")
DB_PATH = os.environ.get("CALC_DB", os.path.abspath(_DEFAULT_DB))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the history table if it does not exist yet."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calculation_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                expression  TEXT NOT NULL,
                result      TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_record(expression: str, result: str) -> dict:
    """Insert one successful calculation and return the stored row."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO calculation_history (expression, result, created_at) "
            "VALUES (?, ?, ?)",
            (expression, result, created_at),
        )
        conn.commit()
        row_id = cur.lastrowid
    finally:
        conn.close()
    return {
        "id": row_id,
        "expression": expression,
        "result": result,
        "created_at": created_at,
    }


def get_all(limit: int = 200) -> list:
    """Return all history rows, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, expression, result, created_at "
            "FROM calculation_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def delete_record(record_id: int) -> bool:
    """Delete a history row by id. Returns True if a row was removed."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM calculation_history WHERE id = ?", (record_id,)
        )
        conn.commit()
        deleted = cur.rowcount > 0
    finally:
        conn.close()
    return deleted
