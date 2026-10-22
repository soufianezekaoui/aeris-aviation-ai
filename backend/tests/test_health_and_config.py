from __future__ import annotations

from fastapi.testclient import TestClient

from aeris.config import Settings
from aeris.main import create_app


def test_health_reports_simulation_only():
    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["simulation_only"] is True
    assert "not a certified aviation system" in body["disclaimer"]


def test_blank_env_values_fall_back_to_defaults(monkeypatch):
    # .env.example ships blank values; they must not break startup.
    monkeypatch.setenv("LLM_PROVIDER", "")
    monkeypatch.setenv("EMBEDDING_MODEL", "")
    s = Settings(_env_file=None)
    assert s.llm_provider == "none"
    assert s.embedding_model == "BAAI/bge-small-en-v1.5"


def test_cors_origin_list_parsing():
    s = Settings(_env_file=None, cors_origins=" http://a.test , http://b.test ,")
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]
