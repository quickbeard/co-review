import pytest
from fastapi import HTTPException

from pr_agent.db.models import GitProvider, GitProviderType
from pr_agent.services.devlake import DevLakeClient, DevLakeSettings, ensure_project_exists


def _provider() -> GitProvider:
    return GitProvider(
        id=7,
        type=GitProviderType.github,
        name="github-main",
        access_token="ghp_testtoken1234567890123456789012345678",
    )


def _client() -> DevLakeClient:
    return DevLakeClient(
        DevLakeSettings(
            base_url="http://localhost:30090",
            api_prefix="/api",
            timeout_sec=30,
            auth_header="Authorization",
            auth_scheme="Bearer",
            token=None,
            verify_tls=True,
        )
    )


def test_project_exists_handles_wrapped_response(monkeypatch: pytest.MonkeyPatch):
    client = _client()
    monkeypatch.setattr(client, "_request", lambda method, path, payload=None, query=None: {"data": {"exist": True}})
    assert client.project_exists("github-7") is True


def test_project_exists_handles_raw_response(monkeypatch: pytest.MonkeyPatch):
    client = _client()
    monkeypatch.setattr(client, "_request", lambda method, path, payload=None, query=None: {"exist": False})
    assert client.project_exists("github-7") is False


def test_ensure_project_exists_creates_when_missing(monkeypatch: pytest.MonkeyPatch):
    client = _client()
    calls = {"exists": 0, "create": 0}

    def fake_exists(name: str) -> bool:
        calls["exists"] += 1
        return False

    def fake_create(name: str, description: str):
        calls["create"] += 1
        assert name == "github-7"
        assert "provider github:7" in description
        return {"name": name}

    monkeypatch.setattr(client, "project_exists", fake_exists)
    monkeypatch.setattr(client, "create_project", fake_create)

    ensure_project_exists(client, project_name="github-7", provider=_provider())
    assert calls == {"exists": 1, "create": 1}


def test_ensure_project_exists_skips_when_present(monkeypatch: pytest.MonkeyPatch):
    client = _client()
    monkeypatch.setattr(client, "project_exists", lambda name: True)
    monkeypatch.setattr(client, "create_project", lambda name, description: (_ for _ in ()).throw(AssertionError("must not create")))

    ensure_project_exists(client, project_name="github-7", provider=_provider())


def test_ensure_project_exists_rejects_empty_name():
    with pytest.raises(HTTPException) as exc:
        ensure_project_exists(_client(), project_name="  ", provider=_provider())
    assert exc.value.status_code == 400
