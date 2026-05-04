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
    UnsupportedWebhookAdapter,
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


class TestGetAdapter:
    def test_github_returns_github_adapter(self):
        assert isinstance(get_adapter(GitProviderType.github), GitHubWebhookAdapter)

    def test_unknown_returns_stub(self):
        adapter = get_adapter(GitProviderType.gitlab)
        assert isinstance(adapter, UnsupportedWebhookAdapter)
