"""Shared pytest fixtures — isolate settings and side-effect paths per test."""
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Mock LLM + Graph dry-run; write audit/db under a temp dir."""
    get_settings.cache_clear()
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("GRAPH_DRY_RUN", "true")
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit_log.jsonl"))
    monkeypatch.setenv("TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
    yield
    get_settings.cache_clear()
