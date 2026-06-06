"""Global audit log in SQLite (same DB as tickets).

Records classification, graph_action, and feedback events.
Plaintext passwords are never stored (see graph_actions._run).
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import get_settings
from .data_io import PROJECT_ROOT

_lock = threading.Lock()


def _path() -> Path:
    p = Path(get_settings().tickets_db_path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_audit_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                kind TEXT NOT NULL,
                data_json TEXT NOT NULL
            )
            """
        )


def log_event(kind: str, **data) -> dict:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        **data,
    }
    payload = {k: v for k, v in entry.items() if k not in ("ts", "kind")}
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO audit_events (ts, kind, data_json) VALUES (?,?,?)",
            (entry["ts"], kind, json.dumps(payload, ensure_ascii=False)),
        )
    return entry


def read_events(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ts, kind, data_json FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        data = json.loads(r["data_json"]) if r["data_json"] else {}
        out.append({"ts": r["ts"], "kind": r["kind"], **data})
    return out
