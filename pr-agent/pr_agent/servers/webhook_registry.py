"""Provider-adapter layer for the webhook-registry feature (P1).

Goal
----
Turn a ``GitProvider`` + ``WebhookRegistration`` into HTTP calls against the
remote git host's webhook API, returning a normalised result shape. Each
adapter encapsulates exactly one provider; callers dispatch via
``get_adapter(provider.type)``.

Supported providers
-------------------
* GitHub (user PAT and App installation tokens) - full support.
* Everything else - stubbed; raises ``NotImplementedError`` so the API layer
  can surface a 501 to the caller without having to know which provider is
  which.
"""
from __future__ import annotations

import importlib
import secrets
from datetime import datetime
from urllib.parse import quote_plus
from abc import ABC, abstractmethod
from datetime import timezone
from typing import Any, Optional

from pr_agent.db.models import (
    GitHubDeploymentType,
    GitProvider,
    GitProviderType,
    WebhookDelivery,
    WebhookRegistration,
)
from pr_agent.log import get_logger


# ---------------------------------------------------------------------------
# Result / error shapes
# ---------------------------------------------------------------------------


class WebhookRegistryError(RuntimeError):
    """Raised when a provider call fails in a way we want to surface verbatim."""

    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class RegistrationResult:
    """Normalised result of a register/unregister/test call."""

    def __init__(
        self,
        *,
        external_id: Optional[str] = None,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        raw: Optional[dict[str, Any]] = None,
    ) -> None:
        self.external_id = external_id
        self.status_code = status_code
        self.message = message
        self.raw = raw or {}


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class WebhookAdapter(ABC):
    """Interface every git provider adapter must implement."""

    @abstractmethod
    def register(
        self, provider: GitProvider, registration: WebhookRegistration
    ) -> RegistrationResult:
        """Create the webhook on the remote provider.

        Returns the provider's external id so we can look it up later.
        """

    @abstractmethod
    def unregister(
        self, provider: GitProvider, registration: WebhookRegistration
    ) -> RegistrationResult:
        """Delete the webhook on the remote provider (if ``external_id`` is set)."""

    @abstractmethod
    def test(
        self, provider: GitProvider, registration: WebhookRegistration
    ) -> RegistrationResult:
        """Trigger a provider-side 'ping' (test delivery)."""

    @abstractmethod
    def list_deliveries(
        self,
        provider: GitProvider,
        registration: WebhookRegistration,
        *,
        limit: int = 30,
    ) -> list[WebhookDelivery]:
        """Return the most recent delivery attempts for this webhook."""


# ---------------------------------------------------------------------------
# GitHub adapter (PyGithub)
# ---------------------------------------------------------------------------


def _split_repo(repo: str) -> tuple[str, str]:
    """Split ``owner/name`` → ``(owner, name)`` with friendly validation errors."""
    if "/" not in repo:
        raise WebhookRegistryError(
            f"GitHub repo must be in 'owner/name' format, got: {repo!r}",
            status_code=400,
        )
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise WebhookRegistryError(
            f"GitHub repo must be in 'owner/name' format, got: {repo!r}",
            status_code=400,
        )
    return owner, name


def _github_client(provider: GitProvider):
    """Build an authenticated PyGithub client for the given provider row."""
    # Imported lazily so non-GitHub deployments don't need PyGithub installed.
    from github import Auth, Github  # type: ignore

    base_url = provider.base_url or "https://api.github.com"

    if provider.deployment_type == GitHubDeploymentType.app:
        # App deployments manage repo hooks via an installation access token.
        # We require the caller to use a PAT for hook management for now;
        # minting a per-repo installation token here adds meaningful complexity
        # (installation lookup, scopes) and the GitHub App itself already gets
        # deliveries via its App-level webhook. Surface a clear error.
        raise WebhookRegistryError(
            "Managing repo-level webhooks requires a user PAT provider; "
            "GitHub App deployments receive deliveries via the App's own "
            "webhook URL (configured at app creation time).",
            status_code=400,
        )

    if not provider.access_token:
        raise WebhookRegistryError(
            "GitHub provider has no access_token set", status_code=400
        )
    return Github(auth=Auth.Token(provider.access_token), base_url=base_url)


def _hook_config(registration: WebhookRegistration) -> dict[str, str]:
    """Build the 'config' dict GitHub expects on POST /hooks."""
    config: dict[str, str] = {
        "url": registration.target_url,
        "content_type": registration.content_type or "json",
        "insecure_ssl": "1" if registration.insecure_ssl else "0",
    }
    if registration.secret:
        config["secret"] = registration.secret
    return config


class GitHubWebhookAdapter(WebhookAdapter):
    """GitHub webhook management via PyGithub."""

    def register(self, provider, registration):
        from github import GithubException  # type: ignore

        owner, name = _split_repo(registration.repo)
        client = _github_client(provider)
        try:
            repo = client.get_repo(f"{owner}/{name}")
            hook = repo.create_hook(
                name="web",
                config=_hook_config(registration),
                events=registration.events or ["push", "pull_request"],
                active=registration.active,
            )
            return RegistrationResult(
                external_id=str(hook.id),
                status_code=201,
                message="Webhook created on GitHub",
                raw={"id": hook.id, "url": hook.url},
            )
        except GithubException as exc:
            raise WebhookRegistryError(
                _github_error_message(exc), status_code=exc.status or 502
            ) from exc
        finally:
            client.close()

    def unregister(self, provider, registration):
        from github import GithubException  # type: ignore

        if not registration.external_id:
            return RegistrationResult(message="No external_id to unregister")

        owner, name = _split_repo(registration.repo)
        client = _github_client(provider)
        try:
            repo = client.get_repo(f"{owner}/{name}")
            hook = repo.get_hook(int(registration.external_id))
            hook.delete()
            return RegistrationResult(
                status_code=204, message="Webhook deleted on GitHub"
            )
        except GithubException as exc:
            # 404 is treated as success (already gone).
            if exc.status == 404:
                return RegistrationResult(
                    status_code=404, message="Webhook already absent on GitHub"
                )
            raise WebhookRegistryError(
                _github_error_message(exc), status_code=exc.status or 502
            ) from exc
        finally:
            client.close()

    def test(self, provider, registration):
        from github import GithubException  # type: ignore

        if not registration.external_id:
            raise WebhookRegistryError(
                "Webhook must be registered before it can be tested",
                status_code=400,
            )

        owner, name = _split_repo(registration.repo)
        client = _github_client(provider)
        try:
            repo = client.get_repo(f"{owner}/{name}")
            hook = repo.get_hook(int(registration.external_id))
            # PyGithub exposes `test()` which hits POST /hooks/{id}/tests.
            hook.test()
            return RegistrationResult(
                status_code=204, message="Test ping dispatched"
            )
        except GithubException as exc:
            raise WebhookRegistryError(
                _github_error_message(exc), status_code=exc.status or 502
            ) from exc
        finally:
            client.close()

    def list_deliveries(self, provider, registration, *, limit=30):
        """List recent webhook deliveries via ``Repository.get_hook_deliveries``.

        Returns [] when the hook id is missing, when GitHub does not support
        deliveries for this deployment (e.g. older GHES), or when the API call fails.
        """
        if not registration.external_id:
            return []
        from github import GithubException  # type: ignore

        owner, name = _split_repo(registration.repo)
        client = _github_client(provider)
        hook_id = int(registration.external_id)
        cap = min(max(limit, 1), 100)
        try:
            repo = client.get_repo(f"{owner}/{name}")
            deliveries = repo.get_hook_deliveries(hook_id)
            out: list[WebhookDelivery] = []
            for delivery in deliveries:
                if len(out) >= cap:
                    break
                delivered_at = delivery.delivered_at
                if delivered_at is not None and delivered_at.tzinfo is not None:
                    delivered_at = delivered_at.astimezone(timezone.utc)
                out.append(
                    WebhookDelivery(
                        id=str(delivery.id),
                        delivered_at=delivered_at,
                        status=delivery.status,
                        status_code=delivery.status_code,
                        event=delivery.event,
                        action=delivery.action,
                        duration_ms=_to_float(delivery.duration),
                        redelivery=bool(delivery.redelivery),
                        url=delivery.url,
                    )
                )
            return out
        except GithubException as exc:
            get_logger().warning(
                f"list_deliveries failed for GitHub: {_github_error_message(exc)}"
            )
            return []
        except Exception as exc:  # noqa: BLE001
            get_logger().warning(f"list_deliveries failed for GitHub: {exc}")
            return []
        finally:
            client.close()


def _github_error_message(exc) -> str:
    """Extract a human-friendly message from a PyGithub ``GithubException``."""
    data = getattr(exc, "data", None) or {}
    if isinstance(data, dict):
        msg = data.get("message") or ""
        errors = data.get("errors") or []
        if errors:
            details = "; ".join(
                str(e.get("message") or e.get("code") or e) for e in errors
            )
            return f"{msg} ({details})".strip() if msg else details
        if msg:
            return msg
    return str(exc)


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# GitLab adapter (python-gitlab)
# ---------------------------------------------------------------------------

_GITLAB_DEFAULT_EVENTS: tuple[str, ...] = (
    "push_events",
    "merge_requests_events",
    "note_events",
)

_GITLAB_EVENT_ALIASES: dict[str, str] = {
    "push": "push_events",
    "push_events": "push_events",
    "push event": "push_events",
    "push events": "push_events",
    "tag_push": "tag_push_events",
    "tag_push_events": "tag_push_events",
    "tag push event": "tag_push_events",
    "tag push events": "tag_push_events",
    "merge_request": "merge_requests_events",
    "merge_requests": "merge_requests_events",
    "merge request": "merge_requests_events",
    "merge request event": "merge_requests_events",
    "merge request events": "merge_requests_events",
    "merge_requests_events": "merge_requests_events",
    "note": "note_events",
    "notes": "note_events",
    "note_events": "note_events",
    "note event": "note_events",
    "note events": "note_events",
    "comment": "note_events",
    "comments": "note_events",
    "issues": "issues_events",
    "issues_events": "issues_events",
    "issue event": "issues_events",
    "issue events": "issues_events",
    "confidential_issues_events": "confidential_issues_events",
    "wiki_page_events": "wiki_page_events",
    "wiki page event": "wiki_page_events",
    "wiki page events": "wiki_page_events",
    "deployment_events": "deployment_events",
    "deployment event": "deployment_events",
    "deployment events": "deployment_events",
    "job_events": "job_events",
    "job event": "job_events",
    "job events": "job_events",
    "pipeline_events": "pipeline_events",
    "pipeline event": "pipeline_events",
    "pipeline events": "pipeline_events",
    "releases_events": "releases_events",
    "release event": "releases_events",
    "release events": "releases_events",
}


def _normalize_gitlab_event_key(event: str) -> Optional[str]:
    key = event.strip().lower().replace("-", "_")
    key = " ".join(key.split())
    if key in _GITLAB_EVENT_ALIASES:
        return _GITLAB_EVENT_ALIASES[key]
    compact = key.replace(" ", "_")
    if compact in _GITLAB_EVENT_ALIASES:
        return _GITLAB_EVENT_ALIASES[compact]
    return None


def _normalize_gitlab_events(events: Optional[list[str]]) -> list[str]:
    if not events:
        return list(_GITLAB_DEFAULT_EVENTS)
    normalized: list[str] = []
    for event in events:
        mapped = _normalize_gitlab_event_key(event)
        if mapped and mapped not in normalized:
            normalized.append(mapped)
    return normalized or list(_GITLAB_DEFAULT_EVENTS)


def _gitlab_client(provider: GitProvider):
    if not provider.access_token:
        raise WebhookRegistryError(
            "GitLab provider has no access_token set", status_code=400
        )
    gitlab = importlib.import_module("gitlab")
    return gitlab.Gitlab(
        url=provider.base_url or "https://gitlab.com",
        private_token=provider.access_token,
    )


def _gitlab_project(client, repo: str):
    if "/" not in repo and not repo.isdigit():
        raise WebhookRegistryError(
            f"GitLab repo must be a numeric project id or 'group/project', got: {repo!r}",
            status_code=400,
        )
    try:
        # Support both "group/project" and URL-encoded "group%2Fproject".
        if repo.isdigit():
            return client.projects.get(int(repo))
        try:
            return client.projects.get(repo)
        except Exception:
            return client.projects.get(quote_plus(repo))
    except Exception as exc:  # noqa: BLE001
        raise WebhookRegistryError(
            f"Unable to resolve GitLab project '{repo}': {exc}",
            status_code=404,
        ) from exc


def _parse_gitlab_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


class GitLabWebhookAdapter(WebhookAdapter):
    """GitLab webhook management via python-gitlab."""

    def register(self, provider, registration):
        client = _gitlab_client(provider)
        try:
            project = _gitlab_project(client, registration.repo)
            payload: dict[str, Any] = {
                "url": registration.target_url,
                "enable_ssl_verification": not bool(registration.insecure_ssl),
            }
            if registration.secret:
                payload["token"] = registration.secret
            for event in _normalize_gitlab_events(registration.events):
                payload[event] = True

            hook = project.hooks.create(payload)
            hook_id = getattr(hook, "id", None)
            return RegistrationResult(
                external_id=str(hook_id) if hook_id is not None else None,
                status_code=201,
                message="Webhook created on GitLab",
                raw=getattr(hook, "attributes", {}) or {},
            )
        except WebhookRegistryError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise WebhookRegistryError(
                f"Failed to register GitLab webhook: {exc}", status_code=502
            ) from exc

    def unregister(self, provider, registration):
        if not registration.external_id:
            return RegistrationResult(message="No external_id to unregister")

        client = _gitlab_client(provider)
        try:
            project = _gitlab_project(client, registration.repo)
            project.hooks.delete(int(registration.external_id))
            return RegistrationResult(
                status_code=204, message="Webhook deleted on GitLab"
            )
        except WebhookRegistryError:
            raise
        except Exception as exc:  # noqa: BLE001
            # GitLab returns 404 when hook was already deleted; treat as success.
            status = getattr(exc, "response_code", None)
            if status == 404:
                return RegistrationResult(
                    status_code=404, message="Webhook already absent on GitLab"
                )
            raise WebhookRegistryError(
                f"Failed to unregister GitLab webhook: {exc}",
                status_code=status or 502,
            ) from exc

    def test(self, provider, registration):
        if not registration.external_id:
            raise WebhookRegistryError(
                "Webhook must be registered before it can be tested",
                status_code=400,
            )

        client = _gitlab_client(provider)
        try:
            project = _gitlab_project(client, registration.repo)
            trigger = _normalize_gitlab_events(registration.events)[0]
            endpoint = (
                f"/projects/{project.encoded_id}/hooks/{int(registration.external_id)}"
                f"/test/{trigger}"
            )
            # Some GitLab versions don't expose this API yet; we degrade
            # gracefully to avoid blocking operators from storing webhooks.
            try:
                client.http_post(endpoint)
                return RegistrationResult(
                    status_code=201, message=f"Test delivery dispatched ({trigger})"
                )
            except Exception as exc:  # noqa: BLE001
                status = getattr(exc, "response_code", None)
                if status in (404, 405):
                    return RegistrationResult(
                        status_code=202,
                        message=(
                            "Test trigger endpoint is unavailable on this GitLab version; "
                            "send a real event to validate deliveries."
                        ),
                    )
                raise
        except WebhookRegistryError:
            raise
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "response_code", None)
            raise WebhookRegistryError(
                f"Failed to trigger GitLab webhook test: {exc}",
                status_code=status or 502,
            ) from exc

    def list_deliveries(self, provider, registration, *, limit=30):
        if not registration.external_id:
            return []

        client = _gitlab_client(provider)
        cap = min(max(limit, 1), 100)
        try:
            project = _gitlab_project(client, registration.repo)
            endpoint = f"/projects/{project.encoded_id}/hooks/{int(registration.external_id)}/events"
            raw = client.http_get(endpoint, query_data={"per_page": cap})

            rows: list[dict[str, Any]]
            if isinstance(raw, list):
                rows = [r for r in raw if isinstance(r, dict)]
            elif isinstance(raw, dict):
                rows = [r for r in raw.get("events", []) if isinstance(r, dict)]
            else:
                return []

            out: list[WebhookDelivery] = []
            for item in rows[:cap]:
                status = item.get("status")
                status_code = item.get("response_status") or item.get("status_code")
                event = item.get("trigger") or item.get("event_name")
                delivered_at = _parse_gitlab_datetime(
                    item.get("created_at") or item.get("execution_timestamp")
                )
                out.append(
                    WebhookDelivery(
                        id=str(item.get("id") or item.get("request_id") or ""),
                        delivered_at=delivered_at,
                        status=status if isinstance(status, str) else None,
                        status_code=status_code if isinstance(status_code, int) else None,
                        event=event if isinstance(event, str) else None,
                        duration_ms=_to_float(
                            item.get("execution_duration") or item.get("duration")
                        ),
                        redelivery=bool(item.get("redelivery") or item.get("retries", 0) > 0),
                        url=item.get("url") if isinstance(item.get("url"), str) else None,
                    )
                )
            return out
        except Exception as exc:  # noqa: BLE001
            get_logger().warning(f"list_deliveries failed for GitLab: {exc}")
            return []


# ---------------------------------------------------------------------------
# Stub adapter for unsupported providers
# ---------------------------------------------------------------------------


class UnsupportedWebhookAdapter(WebhookAdapter):
    """Placeholder raised for providers where webhook management isn't yet wired."""

    def __init__(self, provider_type: GitProviderType) -> None:
        self.provider_type = provider_type

    def _unsupported(self):
        raise WebhookRegistryError(
            f"Webhook management for provider '{self.provider_type.value}' "
            "is not yet implemented",
            status_code=501,
        )

    def register(self, provider, registration):
        self._unsupported()

    def unregister(self, provider, registration):
        self._unsupported()

    def test(self, provider, registration):
        self._unsupported()

    def list_deliveries(self, provider, registration, *, limit=30):
        return []


# ---------------------------------------------------------------------------
# Factory + utilities
# ---------------------------------------------------------------------------


_ADAPTERS: dict[GitProviderType, type[WebhookAdapter]] = {
    GitProviderType.github: GitHubWebhookAdapter,
    GitProviderType.gitlab: GitLabWebhookAdapter,
}


def get_adapter(provider_type: GitProviderType) -> WebhookAdapter:
    """Return the adapter for ``provider_type``, or a stub for unsupported ones."""
    cls = _ADAPTERS.get(provider_type)
    if cls is None:
        return UnsupportedWebhookAdapter(provider_type)
    return cls()


def generate_webhook_secret(num_bytes: int = 32) -> str:
    """Generate a cryptographically-strong secret for a new webhook."""
    return secrets.token_hex(num_bytes)
