import pytest
from fastapi import HTTPException

from pr_agent.db.models import GitProvider, GitProviderType
from pr_agent.services.devlake import (
    DevLakeClient,
    DevLakeSettings,
    apply_scope_selection_and_blueprint,
    cleanup_integration_resources,
    ensure_project_exists,
)


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
        return {"name": name, "blueprint": {"id": 21}}

    monkeypatch.setattr(client, "project_exists", fake_exists)
    monkeypatch.setattr(client, "create_project", fake_create)

    blueprint_id = ensure_project_exists(client, project_name="github-7", provider=_provider())
    assert blueprint_id == 21
    assert calls == {"exists": 1, "create": 1}


def test_ensure_project_exists_skips_when_present(monkeypatch: pytest.MonkeyPatch):
    client = _client()
    monkeypatch.setattr(client, "project_exists", lambda name: True)
    monkeypatch.setattr(client, "create_project", lambda name, description: (_ for _ in ()).throw(AssertionError("must not create")))
    monkeypatch.setattr(client, "get_project", lambda name: {"name": name, "blueprint": {"id": 22}})

    blueprint_id = ensure_project_exists(client, project_name="github-7", provider=_provider())
    assert blueprint_id == 22


def test_ensure_project_exists_rejects_empty_name():
    with pytest.raises(HTTPException) as exc:
        ensure_project_exists(_client(), project_name="  ", provider=_provider())
    assert exc.value.status_code == 400


def test_apply_scope_selection_and_blueprint_creates_when_missing(monkeypatch: pytest.MonkeyPatch):
    from pr_agent.db.models import DevLakeIntegration

    client = _client()
    integration = DevLakeIntegration(
        git_provider_id=7,
        connection_id=11,
        blueprint_id=99,
        project_name="github-7",
        selected_scopes=[{"scopeId": "1", "name": "org/repo"}],
    )
    called = {"put": 0, "patch": 0}

    def fake_put(plugin_name: str, connection_id: int, scopes):
        called["put"] += 1
        assert plugin_name == "github"
        assert connection_id == 11
        assert scopes == [{"scopeId": "1", "name": "org/repo"}]

    monkeypatch.setattr(client, "put_scopes", fake_put)
    monkeypatch.setattr(client, "create_blueprint", lambda payload: (_ for _ in ()).throw(AssertionError("must not create")))
    monkeypatch.setattr(client, "patch_blueprint", lambda blueprint_id, payload: called.__setitem__("patch", called["patch"] + 1) or {"id": blueprint_id})

    bp_id = apply_scope_selection_and_blueprint(
        client,
        plugin_name="github",
        integration=integration,
    )
    assert bp_id == 99
    assert called == {"put": 1, "patch": 1}


def test_apply_scope_selection_and_blueprint_patches_existing(monkeypatch: pytest.MonkeyPatch):
    from pr_agent.db.models import DevLakeIntegration

    client = _client()
    integration = DevLakeIntegration(
        git_provider_id=7,
        connection_id=11,
        blueprint_id=77,
        project_name="github-7",
        selected_scopes=[],
    )
    called = {"put": 0, "patch": 0}

    monkeypatch.setattr(client, "put_scopes", lambda plugin_name, connection_id, scopes: called.__setitem__("put", 1))

    def fake_patch(blueprint_id: int, payload):
        called["patch"] += 1
        assert blueprint_id == 77
        return {"id": 77}

    monkeypatch.setattr(client, "patch_blueprint", fake_patch)
    monkeypatch.setattr(client, "create_blueprint", lambda payload: {"id": 999})

    bp_id = apply_scope_selection_and_blueprint(
        client,
        plugin_name="github",
        integration=integration,
    )
    assert bp_id == 77
    assert called == {"put": 1, "patch": 1}


def test_apply_scope_selection_and_blueprint_requires_blueprint_id():
    from pr_agent.db.models import DevLakeIntegration

    client = _client()
    integration = DevLakeIntegration(
        git_provider_id=7,
        connection_id=11,
        blueprint_id=None,
        project_name="github-7",
        selected_scopes=[],
    )

    with pytest.raises(HTTPException) as exc:
        apply_scope_selection_and_blueprint(
            client,
            plugin_name="github",
            integration=integration,
        )
    assert exc.value.status_code == 500


def test_cleanup_integration_resources_deletes_all(monkeypatch: pytest.MonkeyPatch):
    from pr_agent.db.models import DevLakeIntegration

    client = _client()
    integration = DevLakeIntegration(
        git_provider_id=7,
        connection_id=11,
        blueprint_id=77,
        project_name="github-7",
    )
    called = {"bp": 0, "conn": 0, "proj": 0}

    monkeypatch.setattr(client, "delete_blueprint", lambda blueprint_id: called.__setitem__("bp", blueprint_id))
    monkeypatch.setattr(client, "delete_connection", lambda plugin_name, connection_id: called.__setitem__("conn", connection_id))
    monkeypatch.setattr(client, "delete_project", lambda project_name: called.__setitem__("proj", 1))

    cleanup_integration_resources(
        client,
        plugin_name="github",
        integration=integration,
    )
    assert called == {"bp": 77, "conn": 11, "proj": 1}


def test_normalize_remote_scope_payload_unwraps_data_envelope():
    from pr_agent.services.devlake import _normalize_remote_scope_payload

    raw = {"success": True, "data": {"children": [{"type": "group", "id": "org1"}], "nextPageToken": ""}}
    assert _normalize_remote_scope_payload(raw)["children"][0]["id"] == "org1"


def test_collect_github_drills_remote_scopes_group_id(monkeypatch: pytest.MonkeyPatch):
    from pr_agent.services.devlake import collect_github_remote_scope_repositories_for_selection

    client = _client()

    def fake_page(connection_id: int, *, group_id: str | None, page_token: str | None):
        assert connection_id == 42
        if group_id is None:
            return {
                "children": [{"type": "group", "id": "minhcong", "fullName": "minhcong"}],
                "nextPageToken": "",
            }
        assert group_id == "minhcong"
        return {
            "children": [
                {
                    "type": "scope",
                    "id": "100",
                    "name": "foodhub",
                    "fullName": "minhcong/foodhub",
                    "data": {"fullName": "minhcong/foodhub", "githubId": 100},
                }
            ],
            "nextPageToken": "",
        }

    monkeypatch.setattr(client, "github_remote_scope_page", fake_page)
    monkeypatch.setattr(client, "github_search_remote_scope_page", lambda *a, **k: {})

    scopes = collect_github_remote_scope_repositories_for_selection(client, 42)
    assert len(scopes) == 1
    assert scopes[0]["fullName"] == "minhcong/foodhub"
