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
        if search_term:
            query["searchTerm"] = search_term
        return self._request(
            "GET",
            f"/plugins/{plugin_name}/connections/{connection_id}/remote-scopes",
            query=query,
        )

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
) -> None:
    normalized_name = (project_name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="project_name is required for DevLake project linkage")

    if client.project_exists(normalized_name):
        return

    provider_key = provider.type.value if hasattr(provider.type, "value") else str(provider.type)
    description = f"Managed by PR-Agent for provider {provider_key}:{provider.id}"
    client.create_project(normalized_name, description=description)


def apply_scope_selection_and_blueprint(
    client: DevLakeClient,
    *,
    plugin_name: str,
    integration: DevLakeIntegration,
) -> int:
    """Persist selected scopes and ensure blueprint reflects latest selection."""
    if not integration.connection_id:
        raise HTTPException(status_code=500, detail="Missing DevLake connection_id on integration row")

    selected_scopes = list(integration.selected_scopes or [])
    client.put_scopes(plugin_name, integration.connection_id, selected_scopes)

    payload = build_blueprint_payload(
        integration=integration,
        plugin_name=plugin_name,
    )
    if integration.blueprint_id:
        bp = client.patch_blueprint(integration.blueprint_id, payload)
        bp_id = bp.get("id", integration.blueprint_id)
    else:
        bp = client.create_blueprint(payload)
        bp_id = bp.get("id")

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
