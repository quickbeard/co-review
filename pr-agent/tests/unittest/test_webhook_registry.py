"""Unit tests for webhook registry GitHub adapter helpers."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pr_agent.db.models import (
    GitHubDeploymentType,
    GitProvider,
    GitProviderType,
    WebhookRegistration,
)
from pr_agent.servers.webhook_registry import (
    GitHubWebhookAdapter,
    GitLabWebhookAdapter,
    UnsupportedWebhookAdapter,
    _normalize_gitlab_events,
    get_adapter,
)


def _pat_github_provider() -> GitProvider:
    return GitProvider(
        id=1,
        type=GitProviderType.github,
        name="gh",
        deployment_type=GitHubDeploymentType.user,
        access_token="pat-token",
        base_url="https://api.github.com",
    )


def _registration(*, external_id: str | None = "99") -> WebhookRegistration:
    return WebhookRegistration(
        git_provider_id=1,
        repo="acme/webhook-test",
        target_url="https://hooks.example.com/v1/github",
        external_id=external_id,
        events=["push"],
    )


class TestGitHubWebhookAdapterListDeliveries:
    def test_returns_empty_without_external_id(self):
        adapter = GitHubWebhookAdapter()
        reg = _registration(external_id=None)
        assert adapter.list_deliveries(_pat_github_provider(), reg) == []

    def test_maps_hook_deliveries_and_respects_limit(self):
        adapter = GitHubWebhookAdapter()
        provider = _pat_github_provider()
        reg = _registration()

        d1 = MagicMock()
        d1.id = 10
        d1.delivered_at = datetime(2025, 1, 2, 15, 0, tzinfo=timezone.utc)
        d1.status = "OK"
        d1.status_code = 200
        d1.event = "push"
        d1.action = None
        d1.duration = 42.5
        d1.redelivery = False
        d1.url = "https://api.github.com/delivery"

        d2 = MagicMock()
        d2.id = 11
        d2.delivered_at = None
        d2.status = None
        d2.status_code = None
        d2.event = None
        d2.action = None
        d2.duration = None
        d2.redelivery = True
        d2.url = None

        mock_repo = MagicMock()
        mock_repo.get_hook_deliveries.return_value = [d1, d2]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo

        with patch(
            "pr_agent.servers.webhook_registry._github_client",
            return_value=mock_client,
        ):
            out = GitHubWebhookAdapter().list_deliveries(provider, reg, limit=1)

        mock_client.get_repo.assert_called_once_with("acme/webhook-test")
        mock_repo.get_hook_deliveries.assert_called_once_with(99)
        mock_client.close.assert_called_once()

        assert len(out) == 1
        assert out[0].id == "10"
        assert out[0].delivered_at == d1.delivered_at
        assert out[0].status == "OK"
        assert out[0].status_code == 200
        assert out[0].event == "push"
        assert out[0].duration_ms == 42.5
        assert out[0].redelivery is False
        assert out[0].url == "https://api.github.com/delivery"

    def test_github_exception_returns_empty_and_logs(self):
        from github import GithubException  # type: ignore

        adapter = GitHubWebhookAdapter()
        provider = _pat_github_provider()
        reg = _registration()

        mock_client = MagicMock()
        mock_client.get_repo.side_effect = GithubException(
            404,
            {"message": "Not Found"},
            headers=None,
        )

        with patch(
            "pr_agent.servers.webhook_registry._github_client",
            return_value=mock_client,
        ):
            with patch("pr_agent.servers.webhook_registry.get_logger") as mock_log:
                out = adapter.list_deliveries(provider, reg)

        assert out == []
        mock_log.return_value.warning.assert_called_once()
        mock_client.close.assert_called_once()


class TestUnsupportedWebhookAdapter:
    def test_list_deliveries_empty(self):
        adapter = UnsupportedWebhookAdapter(GitProviderType.gitlab)
        assert (
            adapter.list_deliveries(MagicMock(), MagicMock(), limit=10) == []
        )


def _gitlab_provider() -> GitProvider:
    return GitProvider(
        id=2,
        type=GitProviderType.gitlab,
        name="gl",
        access_token="x",
        base_url="https://gitlab.example.com",
    )


def _gitlab_registration(*, external_id: str | None = "55") -> WebhookRegistration:
    return WebhookRegistration(
        git_provider_id=2,
        repo="acme/group/repo",
        target_url="https://hooks.example.com/v1/gitlab",
        external_id=external_id,
        events=["merge request events", "push_events", "note events"],
        insecure_ssl=False,
    )


class TestGitLabHelpers:
    def test_normalize_gitlab_events(self):
        assert _normalize_gitlab_events(None) == [
            "push_events",
            "merge_requests_events",
            "note_events",
        ]
        assert _normalize_gitlab_events(
            ["merge request events", "push", "notes", "unknown"]
        ) == [
            "merge_requests_events",
            "push_events",
            "note_events",
        ]


class TestGitLabWebhookAdapter:
    def test_register_creates_hook_with_normalized_events(self):
        adapter = GitLabWebhookAdapter()
        provider = _gitlab_provider()
        registration = _gitlab_registration()

        hook = MagicMock()
        hook.id = 777
        hook.attributes = {"id": 777}

        project = MagicMock()
        project.hooks.create.return_value = hook

        client = MagicMock()
        client.projects.get.return_value = project

        with patch(
            "pr_agent.servers.webhook_registry._gitlab_client",
            return_value=client,
        ):
            result = adapter.register(provider, registration)

        project.hooks.create.assert_called_once()
        payload = project.hooks.create.call_args.args[0]
        assert payload["url"] == registration.target_url
        assert payload["merge_requests_events"] is True
        assert payload["push_events"] is True
        assert payload["note_events"] is True
        assert result.external_id == "777"
        assert result.status_code == 201

    def test_unregister_returns_success_on_404(self):
        adapter = GitLabWebhookAdapter()
        provider = _gitlab_provider()
        registration = _gitlab_registration(external_id="101")

        class _NotFoundError(Exception):
            response_code = 404

        project = MagicMock()
        project.hooks.delete.side_effect = _NotFoundError("gone")
        client = MagicMock()
        client.projects.get.return_value = project

        with patch(
            "pr_agent.servers.webhook_registry._gitlab_client",
            return_value=client,
        ):
            result = adapter.unregister(provider, registration)

        assert result.status_code == 404

    def test_test_webhook_gracefully_handles_unsupported_endpoint(self):
        adapter = GitLabWebhookAdapter()
        provider = _gitlab_provider()
        registration = _gitlab_registration(external_id="101")

        class _MethodNotAllowedError(Exception):
            response_code = 405

        project = MagicMock()
        project.encoded_id = "acme%2Fgroup%2Frepo"

        client = MagicMock()
        client.projects.get.return_value = project
        client.http_post.side_effect = _MethodNotAllowedError("not supported")

        with patch(
            "pr_agent.servers.webhook_registry._gitlab_client",
            return_value=client,
        ):
            result = adapter.test(provider, registration)

        assert result.status_code == 202
        assert "unavailable" in (result.message or "")

    def test_list_deliveries_maps_rows(self):
        adapter = GitLabWebhookAdapter()
        provider = _gitlab_provider()
        registration = _gitlab_registration(external_id="88")

        project = MagicMock()
        project.encoded_id = "acme%2Fgroup%2Frepo"

        client = MagicMock()
        client.projects.get.return_value = project
        client.http_get.return_value = [
            {
                "id": 1,
                "status": "successful",
                "response_status": 200,
                "trigger": "push_events",
                "execution_duration": 1.5,
                "created_at": "2026-01-10T10:00:00Z",
                "url": registration.target_url,
            }
        ]

        with patch(
            "pr_agent.servers.webhook_registry._gitlab_client",
            return_value=client,
        ):
            out = adapter.list_deliveries(provider, registration, limit=10)

        assert len(out) == 1
        assert out[0].id == "1"
        assert out[0].status_code == 200
        assert out[0].event == "push_events"
        assert out[0].duration_ms == 1.5


class TestGetAdapter:
    def test_github_returns_github_adapter(self):
        assert isinstance(get_adapter(GitProviderType.github), GitHubWebhookAdapter)

    def test_unknown_returns_stub(self):
        adapter = get_adapter(GitProviderType.gitlab)
        assert isinstance(adapter, GitLabWebhookAdapter)
