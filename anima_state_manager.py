import json
import os
import sqlite3
import threading

from anima_path import STATE_DB

_db_lock   = threading.Lock()
_conn      = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(STATE_DB, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT)"
        )
        _conn.commit()
    return _conn


def get_all() -> dict:
    with _db_lock:
        cur = _get_conn().execute("SELECT key, value FROM state")
        return {k: json.loads(v) for k, v in cur.fetchall()}


def get(key: str, default=None):
    with _db_lock:
        cur = _get_conn().execute("SELECT value FROM state WHERE key = ?", (key,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else default


def set_value(key: str, value):
    with _db_lock:
        _get_conn().execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        _get_conn().commit()


def update_state(data: dict):
    with _db_lock:
        conn = _get_conn()
        for k, v in data.items():
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (k, json.dumps(v, ensure_ascii=False)),
            )
        conn.commit()
