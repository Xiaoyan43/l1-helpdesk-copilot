"""Rule baseline classifier tests (offline, no API)."""
from app.classifier import rule_based_classify
from app.models import Category, Impact, Priority, Ticket, TicketType, Urgency


def _ticket(subject: str, body: str) -> Ticket:
    return Ticket(subject=subject, body=body)


def test_password_incident_maps_to_account_access_and_kb001():
    t = _ticket(
        "Can't log in - account locked",
        "I tried my password too many times and now I'm locked out of my laptop and email.",
    )
    cl = rule_based_classify(t)
    assert cl.category == Category.account_access
    assert cl.ticket_type == TicketType.incident
    assert cl.kb_hit == "KB001"
    assert cl.source == "mock"


def test_new_hire_request_maps_to_account_access():
    t = _ticket(
        "New hire setup - Maria Chen",
        (
            "Please create her account, add her to the Sales distribution group, "
            "and assign an Office license."
        ),
    )
    cl = rule_based_classify(t)
    assert cl.category == Category.account_access
    assert cl.ticket_type == TicketType.request
    assert cl.impact == Impact.low


def test_vpn_incident_maps_to_network_and_kb002():
    t = _ticket(
        "VPN keeps disconnecting",
        "Since the update yesterday my VPN drops every few minutes when I work from home.",
    )
    cl = rule_based_classify(t)
    assert cl.category == Category.network
    assert cl.kb_hit == "KB002"


def test_phishing_maps_to_security_high_priority():
    t = _ticket(
        "Suspicious activity report",
        "I received a phishing message pretending to be IT. Reporting malware just in case.",
    )
    cl = rule_based_classify(t)
    assert cl.category == Category.security
    assert cl.priority == Priority.high
    assert cl.kb_hit == "KB006"


def test_site_outage_maps_to_critical():
    t = _ticket(
        "Whole office internet is down",
        "Nobody in the London office can connect to anything. This is blocking the entire team.",
    )
    cl = rule_based_classify(t)
    assert cl.category == Category.network
    assert cl.priority == Priority.critical
    assert cl.impact == Impact.high
    assert cl.urgency == Urgency.high


def test_unrelated_text_falls_back_to_other():
    t = _ticket("General question", "What time does the cafeteria open?")
    cl = rule_based_classify(t)
    assert cl.category == Category.other
    assert cl.kb_hit is None
    assert cl.priority == Priority.low
