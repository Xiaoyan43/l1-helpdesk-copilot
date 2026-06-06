"""Audit log tests."""
import json

from app.audit import log_event, read_events


def test_log_event_appends_jsonl():
    # conftest already points AUDIT_LOG_PATH at tmp_path/audit_log.jsonl
    entry = log_event("classification", ticket_id="T001", category="network")
    assert entry["kind"] == "classification"
    assert entry["ticket_id"] == "T001"

    events = read_events()
    assert len(events) == 1
    assert events[0]["category"] == "network"


def test_read_events_returns_newest_first(tmp_path):
    log_event("classification", seq=1)
    log_event("classification", seq=2)
    events = read_events(limit=2)
    assert [e["seq"] for e in events] == [2, 1]


def test_audit_file_never_contains_plaintext_password(tmp_path):
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
    raw = (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8")
    assert secret not in raw
    for line in raw.splitlines():
        parsed = json.loads(line)
        assert "generated_password" not in parsed
