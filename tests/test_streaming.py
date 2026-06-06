"""Streaming reply smoke tests."""
import json

from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.models import Category, Classification, Impact, Priority, Ticket, TicketType, Urgency
from app.responder import stream_reply


def test_stream_reply_mock_yields_text():
    ticket = Ticket(subject="VPN drops", body="My vpn keeps disconnecting at home.", requester="u@lab.com")
    cl = Classification(
        category=Category.network,
        priority=Priority.medium,
        ticket_type=TicketType.incident,
        impact=Impact.low,
        urgency=Urgency.medium,
        kb_hit="KB002",
        confidence=0.8,
    )
    from app.kb import load_articles

    articles = load_articles("kb")[:2]
    text = "".join(stream_reply(ticket, cl, articles))
    assert "IT Service Desk" in text
    assert len(text) > 50


def test_respond_stream_returns_sse_done(isolated_settings):
    store.init_db()
    store.seed_if_empty()
    tickets = store.list_tickets()
    assert tickets

    client = TestClient(app)
    resp = client.post(f"/tickets/{tickets[0].id}/respond/stream")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = []
    for block in resp.text.strip().split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))

    assert events[0]["type"] == "meta"
    assert events[-1]["type"] == "done"
    assert events[-1]["reply_text"]
    assert "token" in {e["type"] for e in events}
