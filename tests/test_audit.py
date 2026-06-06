"""Audit log tests."""
import json
import sqlite3

from app.audit import log_event, read_events
from app.config import get_settings


def test_log_event_persists_to_sqlite():
    entry = log_event("classification", ticket_id="T001", category="network")
    assert entry["kind"] == "classification"
    assert entry["ticket_id"] == "T001"

    events = read_events()
    assert len(events) == 1
    assert events[0]["category"] == "network"


def test_read_events_returns_newest_first():
    log_event("classification", seq=1)
    log_event("classification", seq=2)
    events = read_events(limit=2)
    assert [e["seq"] for e in events] == [2, 1]


def test_audit_db_never_contains_plaintext_password():
    from app.graph_actions import create_user
    from app.models import CreateUserRequest

    secret = "PlaintextSecret1!"
    create_user(
        CreateUserRequest(
            display_name="Audit Test",
            user_principal_name="audit@lab.onmicrosoft.com",
            password=secret,
        )
    )
    db_path = get_settings().tickets_db_path
    with sqlite3.connect(db_path) as conn:
        raw = "\n".join(
            str(r[0]) for r in conn.execute("SELECT data_json FROM audit_events").fetchall()
        )
    assert secret not in raw
    for event in read_events():
        assert "generated_password" not in event
