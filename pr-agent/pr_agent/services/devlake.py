"""
Helpers for orchestrating Apache DevLake integration.

This module intentionally keeps the integration explicit and backend-only:
- read provider credentials from our DB
- call DevLake APIs to create connection/scopes/blueprint
- trigger ingestion and return pipeline metadata
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from fastapi import HTTPException

from pr_agent.db import DevLakeIntegration, GitProvider

# GitHub DevLake remote-scopes: groupId="" returns org/user *folders* only; repos come from
# remote-scopes?groupId=<owner>. See apache/incubator-devlake backend/plugins/github/api/remote_api.go
GITHUB_REMOTE_PREVIEW_MAX_REPOS = int(os.environ.get("DEVLAKE_GITHUB_REMOTE_PREVIEW_MAX_REPOS", "400"))
GITHUB_REMOTE_PREVIEW_SEARCH_MAX_PAGES = int(os.environ.get("DEVLAKE_GITHUB_REMOTE_PREVIEW_SEARCH_MAX_PAGES", "30"))
GITHUB_REMOTE_PREVIEW_OWNER_LIST_MAX_PAGES = int(os.environ.get("DEVLAKE_GITHUB_REMOTE_PREVIEW_OWNER_LIST_MAX_PAGES", "40"))


def _normalize_remote_scope_payload(raw: Any) -> dict[str, Any]:
    """Unwrap DevLake {data: {children,...}} and similar envelopes."""
    if not isinstance(raw, dict):
        return {}
    nested = raw.get("data")
    if isinstance(nested, dict) and ("children" in nested or "nextPageToken" in nested):
        return nested
    if "children" in raw or "nextPageToken" in raw:
        return raw
    inner = DevLakeClient._unwrap_data(raw)
    return inner if isinstance(inner, dict) else {}


def _github_remote_scope_entry_type(entry: dict[str, Any]) -> str:
    t = entry.get("type")
    return str(t).strip().lower() if isinstance(t, str) else ""


def _github_owner_slug(entry: dict[str, Any]) -> str | None:
    for key in ("id", "fullName", "name"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _github_entry_looks_like_repository(entry: dict[str, Any]) -> bool:
    if _github_remote_scope_entry_type(entry) == "scope":
        return True
    fn = entry.get("fullName")
    if isinstance(fn, str) and "/" in fn:
        return True
    data = entry.get("data")
    if isinstance(data, dict):
        if data.get("fullName"):
            return True
        if data.get("githubId") is not None:
            return True
    return False


def _normalize_github_remote_scope_entry(entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    data = out.get("data")
    if isinstance(data, dict):
        if out.get("fullName") is None and isinstance(data.get("fullName"), str):
            out["fullName"] = data["fullName"]
        if out.get("name") is None and isinstance(data.get("name"), str):
            out["name"] = data["name"]
    if out.get("scopeId") is None and out.get("id") is not None:
        out["scopeId"] = str(out["id"])
    return out


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class DevLakeSettings:
    base_url: str
    api_prefix: str
    timeout_sec: float
    auth_header: str
    auth_scheme: str
    token: str | None
    verify_tls: bool


def load_settings() -> DevLakeSettings:
    base_url = os.environ.get("DEVLAKE_API_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail="DEVLAKE_API_BASE_URL is not configured",
        )

    api_prefix = os.environ.get("DEVLAKE_API_PREFIX", "/api").strip()
    if not api_prefix.startswith("/"):
        api_prefix = f"/{api_prefix}"
    api_prefix = api_prefix.rstrip("/")

    return DevLakeSettings(
        base_url=base_url,
        api_prefix=api_prefix,
        timeout_sec=float(os.environ.get("DEVLAKE_API_TIMEOUT_SEC", "30")),
        auth_header=os.environ.get("DEVLAKE_API_AUTH_HEADER", "Authorization"),
        auth_scheme=os.environ.get("DEVLAKE_API_AUTH_SCHEME", "Bearer"),
        token=os.environ.get("DEVLAKE_API_TOKEN"),
        verify_tls=_env_bool("DEVLAKE_API_VERIFY_TLS", True),
    )


class DevLakeClient:
    def __init__(self, settings: DevLakeSettings):
        self.settings = settings

    @staticmethod
    def _redact_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if payload is None:
            return None
        redacted = dict(payload)
        for key in ("token", "secretKey", "password", "privateKey", "refreshToken"):
            if key in redacted and redacted[key]:
                redacted[key] = "***REDACTED***"
        return redacted

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        prefix = self.settings.api_prefix
        if normalized_path.startswith(prefix):
            full_path = normalized_path
        else:
            full_path = f"{prefix}{normalized_path}"
        url = f"{self.settings.base_url}{full_path}"
        if query:
            url = f"{url}?{parse.urlencode(query, doseq=True)}"
        return url

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        *,
        allow_not_found: bool = False,
    ) -> Any:
        url = self._build_url(path, query=query)
        body = None
        headers: dict[str, str] = {"Accept": "application/json"}

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if self.settings.token:
            token_value = self.settings.token
            if self.settings.auth_scheme:
                token_value = f"{self.settings.auth_scheme} {token_value}"
            headers[self.settings.auth_header] = token_value

        req = request.Request(url=url, data=body, headers=headers, method=method.upper())
        try:
            with request.urlopen(req, timeout=self.settings.timeout_sec) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return {}
            detail = exc.read().decode("utf-8", errors="ignore")
            safe_payload = self._redact_payload(payload)
            raise HTTPException(
                status_code=502,
                detail=(
                    f"DevLake API error ({exc.code}) on {method.upper()} {url}: "
                    f"{detail or exc.reason}. payload={safe_payload}"
                ),
            ) from exc
        except error.URLError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Cannot reach DevLake API: {exc.reason}",
            ) from exc

    @staticmethod
    def _unwrap_data(raw: Any) -> Any:
        """Support both raw-object and {data: ...} response envelopes."""
        if isinstance(raw, dict) and "data" in raw:
            return raw.get("data")
        return raw

    def create_connection(self, plugin_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/plugins/{plugin_name}/connections", payload=payload)

    def delete_connection(self, plugin_name: str, connection_id: int, *, allow_not_found: bool = True) -> Any:
        return self._request(
            "DELETE",
            f"/plugins/{plugin_name}/connections/{connection_id}",
            allow_not_found=allow_not_found,
        )

    def project_exists(self, project_name: str) -> bool:
        encoded_name = parse.quote(project_name, safe="")
        raw = self._request("GET", f"/projects/{encoded_name}/check")
        body = self._unwrap_data(raw)
        if isinstance(body, dict) and isinstance(body.get("exist"), bool):
            return body["exist"]
        raise HTTPException(status_code=502, detail=f"Unexpected DevLake project-check payload: {raw}")

    def create_project(self, project_name: str, description: str) -> dict[str, Any]:
        raw = self._request(
            "POST",
            "/projects",
            payload={
                "name": project_name,
                "description": description,
            },
        )
        body = self._unwrap_data(raw)
        if isinstance(body, dict):
            return body
        raise HTTPException(status_code=502, detail=f"Unexpected DevLake project payload: {raw}")

    def get_project(self, project_name: str) -> dict[str, Any]:
        encoded_name = parse.quote(project_name, safe="")
        raw = self._request("GET", f"/projects/{encoded_name}")
        body = self._unwrap_data(raw)
        if isinstance(body, dict):
            return body
        raise HTTPException(status_code=502, detail=f"Unexpected DevLake project payload: {raw}")

    def delete_project(self, project_name: str, *, allow_not_found: bool = True) -> Any:
        encoded_name = parse.quote(project_name, safe="")
        return self._request(
            "DELETE",
            f"/projects/{encoded_name}",
            allow_not_found=allow_not_found,
        )

    def list_remote_scopes(
        self,
        plugin_name: str,
        connection_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        search_term: str | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {"page": page, "pageSize": page_size}
        # GitHub uses groupId/pageToken pagination (see Swagger); remote-scopes does not use searchTerm.
        if plugin_name != "github" and search_term:
            query["searchTerm"] = search_term
        raw = self._request(
            "GET",
            f"/plugins/{plugin_name}/connections/{connection_id}/remote-scopes",
            query=query,
        )
        return _normalize_remote_scope_payload(raw)

    def github_remote_scope_page(
        self,
        connection_id: int,
        *,
        group_id: str | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if group_id:
            query["groupId"] = group_id
        if page_token:
            query["pageToken"] = page_token
        raw = self._request(
            "GET",
            f"/plugins/github/connections/{connection_id}/remote-scopes",
            query=query if query else None,
        )
        return _normalize_remote_scope_payload(raw)

    def github_search_remote_scope_page(
        self,
        connection_id: int,
        *,
        search: str,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        raw = self._request(
            "GET",
            f"/plugins/github/connections/{connection_id}/search-remote-scopes",
            query={
                "search": search.strip(),
                "page": page,
                "pageSize": page_size,
            },
        )
        return _normalize_remote_scope_payload(raw)

    def put_scopes(self, plugin_name: str, connection_id: int, scopes: list[dict[str, Any]]) -> Any:
        return self._request(
            "PUT",
            f"/plugins/{plugin_name}/connections/{connection_id}/scopes",
            payload={"data": scopes},
        )

    def create_blueprint(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/blueprints", payload=payload)

    def delete_blueprint(self, blueprint_id: int, *, allow_not_found: bool = True) -> Any:
        return self._request(
            "DELETE",
            f"/blueprints/{blueprint_id}",
            allow_not_found=allow_not_found,
        )

    def patch_blueprint(self, blueprint_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/blueprints/{blueprint_id}", payload=payload)

    def trigger_blueprint(
        self,
        blueprint_id: int,
        *,
        full_sync: bool = False,
        skip_collectors: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/blueprints/{blueprint_id}/trigger",
            payload={"fullSync": full_sync, "skipCollectors": skip_collectors},
        )


def _next_remote_scope_page_token(body: dict[str, Any]) -> str | None:
    tok = body.get("nextPageToken")
    if isinstance(tok, str) and tok.strip():
        return tok.strip()
    return None


def collect_github_remote_scope_repositories_for_selection(
    client: DevLakeClient,
    connection_id: int,
    *,
    search_term: str | None = None,
    max_repos: int = GITHUB_REMOTE_PREVIEW_MAX_REPOS,
) -> list[dict[str, Any]]:
    """Enumerate GitHub repositories via DevLake remote API (groups first, then per-owner repos).

    `/plugins/github/connections/{id}/scopes` GET lists *configured* repos on the connection, not discovery.
    Discovery is `/remote-scopes` with optional `groupId` + pagination, per DevLake Swagger.
    """
    trimmed = (search_term or "").strip()
    out: list[dict[str, Any]] = []
    seen_key: set[str] = set()

    def take_entry(entry: dict[str, Any]) -> None:
        if not _github_entry_looks_like_repository(entry):
            return
        row = _normalize_github_remote_scope_entry(entry)
        key = row.get("fullName") or row.get("scopeId") or str(row.get("id", ""))
        if not isinstance(key, str) or not key:
            return
        if key in seen_key:
            return
        seen_key.add(key)
        out.append(row)

    if trimmed:
        ps = min(100, max(1, max_repos))
        for page in range(1, GITHUB_REMOTE_PREVIEW_SEARCH_MAX_PAGES + 1):
            body = client.github_search_remote_scope_page(
                connection_id, search=trimmed, page=page, page_size=ps
            )
            children = body.get("children") or []
            for ch in children:
                if isinstance(ch, dict):
                    take_entry(ch)
            if len(out) >= max_repos or len(children) < ps:
                break
        return out

    owner_order: list[str] = []
    seen_owners: set[str] = set()
    pt: str | None = None
    for _ in range(GITHUB_REMOTE_PREVIEW_OWNER_LIST_MAX_PAGES):
        body = client.github_remote_scope_page(connection_id, group_id=None, page_token=pt)
        batch = body.get("children") or []
        for entry in batch:
            if not isinstance(entry, dict):
                continue
            if _github_remote_scope_entry_type(entry) != "group":
                continue
            slug = _github_owner_slug(entry)
            if slug and slug not in seen_owners:
                seen_owners.add(slug)
                owner_order.append(slug)
        nxt = _next_remote_scope_page_token(body)
        if not nxt:
            break
        pt = nxt

    for oid in owner_order:
        pg: str | None = None
        while len(out) < max_repos:
            body = client.github_remote_scope_page(connection_id, group_id=oid, page_token=pg)
            for entry in body.get("children") or []:
                if isinstance(entry, dict):
                    take_entry(entry)
            if len(out) >= max_repos:
                return out
            nxt = _next_remote_scope_page_token(body)
            if not nxt:
                break
            pg = nxt
        if len(out) >= max_repos:
            break

    return out


def _normalize_devlake_rest_endpoint(endpoint: str) -> str:
    """DevLake RestConnection.GetEndpoint() expects a trailing slash for API roots."""
    e = endpoint.strip()
    if not e:
        return e
    return e if e.endswith("/") else f"{e}/"


def map_provider_to_plugin(provider: GitProvider) -> str:
    mapping = {
        "github": "github",
        "gitlab": "gitlab",
        "bitbucket": "bitbucket",
        "azure_devops": "azuredevops",
    }
    key = provider.type.value if hasattr(provider.type, "value") else str(provider.type)
    plugin = mapping.get(key)
    if not plugin:
        raise HTTPException(
            status_code=400,
            detail=f"DevLake integration is not yet supported for provider type '{key}'",
        )
    return plugin


def build_connection_payload(provider: GitProvider, plugin_name: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": provider.name}

    if plugin_name == "github":
        payload["authMethod"] = "AccessToken"
        payload["endpoint"] = _normalize_devlake_rest_endpoint(
            provider.base_url or "https://api.github.com/"
        )
        if not provider.access_token:
            raise HTTPException(status_code=400, detail="GitHub provider requires access_token for DevLake sync")
        payload["token"] = provider.access_token
    elif plugin_name == "gitlab":
        payload["endpoint"] = _normalize_devlake_rest_endpoint(
            provider.base_url or "https://gitlab.com/api/v4/"
        )
        if not provider.access_token:
            raise HTTPException(status_code=400, detail="GitLab provider requires access_token for DevLake sync")
        payload["token"] = provider.access_token
    elif plugin_name == "bitbucket":
        payload["endpoint"] = provider.base_url or "https://api.bitbucket.org/2.0"
        if not provider.access_token:
            raise HTTPException(status_code=400, detail="Bitbucket provider requires access_token for DevLake sync")
        payload["token"] = provider.access_token
    elif plugin_name == "azuredevops":
        payload["endpoint"] = provider.base_url or "https://dev.azure.com"
        token = provider.pat or provider.access_token
        if not token:
            raise HTTPException(status_code=400, detail="Azure DevOps provider requires pat/access_token for DevLake sync")
        payload["token"] = token
        if provider.organization:
            payload["organization"] = provider.organization

    return payload


def build_blueprint_payload(
    *,
    integration: DevLakeIntegration,
    plugin_name: str,
) -> dict[str, Any]:
    if not integration.connection_id:
        raise HTTPException(status_code=500, detail="Missing DevLake connection_id on integration row")
    if not integration.project_name:
        raise HTTPException(status_code=400, detail="project_name is required for DevLake sync")

    selected_scopes = integration.selected_scopes or []
    blueprint_scopes = []
    for scope in selected_scopes:
        scope_id = scope.get("scopeId") or scope.get("id")
        if scope_id is None:
            continue
        blueprint_scopes.append({"scopeId": str(scope_id)})

    return {
        "name": f"{integration.project_name}-BLUEPRINT",
        "projectName": integration.project_name,
        "mode": "NORMAL",
        "enable": True,
        "cronConfig": "manual",
        "isManual": True,
        "skipOnFail": False,
        "skipCollectors": False,
        "fullSync": False,
        "connections": [
            {
                "pluginName": plugin_name,
                "connectionId": integration.connection_id,
                "scopes": blueprint_scopes,
            }
        ],
    }


def ensure_project_exists(
    client: DevLakeClient,
    *,
    project_name: str,
    provider: GitProvider,
) -> int | None:
    normalized_name = (project_name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="project_name is required for DevLake project linkage")

    if client.project_exists(normalized_name):
        project = client.get_project(normalized_name)
    else:
        provider_key = provider.type.value if hasattr(provider.type, "value") else str(provider.type)
        description = f"Managed by PR-Agent for provider {provider_key}:{provider.id}"
        project = client.create_project(normalized_name, description=description)

    blueprint = project.get("blueprint")
    if isinstance(blueprint, dict) and isinstance(blueprint.get("id"), int):
        return blueprint["id"]
    return None


def apply_scope_selection_and_blueprint(
    client: DevLakeClient,
    *,
    plugin_name: str,
    integration: DevLakeIntegration,
) -> int:
    """Persist selected scopes and patch the project-linked blueprint."""
    if not integration.connection_id:
        raise HTTPException(status_code=500, detail="Missing DevLake connection_id on integration row")
    if not integration.blueprint_id:
        raise HTTPException(status_code=500, detail="Missing DevLake blueprint_id on integration row")

    selected_scopes = list(integration.selected_scopes or [])
    client.put_scopes(plugin_name, integration.connection_id, selected_scopes)

    payload = build_blueprint_payload(
        integration=integration,
        plugin_name=plugin_name,
    )
    bp = client.patch_blueprint(integration.blueprint_id, payload)
    bp_id = bp.get("id", integration.blueprint_id)

    if not isinstance(bp_id, int):
        raise HTTPException(status_code=502, detail=f"Unexpected DevLake blueprint payload: {bp}")
    return bp_id


def cleanup_integration_resources(
    client: DevLakeClient,
    *,
    plugin_name: str,
    integration: DevLakeIntegration,
) -> None:
    """Delete DevLake resources created for an integration row."""
    if integration.blueprint_id:
        client.delete_blueprint(integration.blueprint_id)
    if integration.connection_id:
        client.delete_connection(plugin_name, integration.connection_id)
    if integration.project_name:
        client.delete_project(integration.project_name)
