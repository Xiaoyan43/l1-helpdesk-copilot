"""Microsoft Graph dry-run + password redaction tests."""
from app.audit import read_events
from app.graph_actions import (
    _redact,
    add_to_group,
    assign_license,
    create_user,
    gen_password,
    reset_password,
)
from app.models import (
    AddToGroupRequest,
    AssignLicenseRequest,
    CreateUserRequest,
    ResetPasswordRequest,
)


def test_gen_password_meets_complexity():
    pwd = gen_password()
    assert len(pwd) == 16
    assert any(c.islower() for c in pwd)
    assert any(c.isupper() for c in pwd)
    assert any(c.isdigit() for c in pwd)
    assert any(c in "!@#$%^&*" for c in pwd)


def test_redact_masks_password_profile_and_top_level_password():
    body = {
        "passwordProfile": {"forceChangePasswordNextSignIn": True, "password": "Secret1!"},
        "password": "Secret1!",
    }
    safe = _redact(body)
    assert safe["passwordProfile"]["password"] == "***REDACTED***"
    assert safe["password"] == "***REDACTED***"
    assert body["passwordProfile"]["password"] == "Secret1!"


def test_create_user_dry_run_redacts_request_and_audit():
    secret = "TempPassw0rd!"
    res = create_user(
        CreateUserRequest(
            display_name="Test User",
            user_principal_name="test@lab.onmicrosoft.com",
            password=secret,
        )
    )
    assert res.dry_run is True
    assert res.success is True
    assert res.generated_password == secret
    assert res.request["body"]["passwordProfile"]["password"] == "***REDACTED***"

    events = read_events(limit=1)
    assert len(events) == 1
    assert events[0]["kind"] == "graph_action"
    assert events[0]["action"] == "create_user"
    assert "generated_password" not in events[0]
    assert events[0]["request"]["body"]["passwordProfile"]["password"] == "***REDACTED***"


def test_reset_password_dry_run_redacts_request():
    secret = "NewPassw0rd!"
    res = reset_password(
        ResetPasswordRequest(user="alice@lab.onmicrosoft.com", new_password=secret)
    )
    assert res.dry_run is True
    assert res.generated_password == secret
    assert res.request["body"]["passwordProfile"]["password"] == "***REDACTED***"


def test_add_to_group_dry_run_without_credentials():
    res = add_to_group(
        AddToGroupRequest(user="user-id", group="group-id")
    )
    assert res.dry_run is True
    assert res.success is True
    assert res.request["method"] == "POST"
    assert "/groups/group-id/members/$ref" in res.request["url"]


def test_assign_license_dry_run_without_credentials():
    res = assign_license(
        AssignLicenseRequest(user="user-id", sku="sku-id")
    )
    assert res.dry_run is True
    assert res.success is True
    assert res.request["body"]["addLicenses"][0]["skuId"] == "sku-id"
