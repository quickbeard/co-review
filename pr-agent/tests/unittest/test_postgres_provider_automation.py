"""Tests for DB-backed automation config applied via ``postgres_provider``."""

import os
from unittest.mock import MagicMock, patch

import pytest

from pr_agent.secret_providers import postgres_provider


@pytest.fixture(autouse=True)
def reset_postgres_config_cache():
    """Isolate TTL globals across tests."""
    postgres_provider.invalidate_postgres_config_cache()
    yield
    postgres_provider.invalidate_postgres_config_cache()


class TestApplyAutomationConfigToSettings:
    def test_no_database_url_is_noop(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with patch.object(
            postgres_provider, "_fetch_automation_config"
        ) as mock_fetch:
            postgres_provider.apply_automation_config_to_settings()
        mock_fetch.assert_not_called()

    def test_writes_disable_auto_feedback_and_provider_keys(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")

        fake_config = {
            "disable_auto_feedback": True,
            "github_app_config": {
                "pr_commands": ["/review"],
                "unknown_key": "ignored",
            },
            "gitlab_config": {"push_commands": ["/describe"]},
        }

        settings = MagicMock()
        with patch.object(
            postgres_provider,
            "_fetch_automation_config",
            return_value=fake_config,
        ):
            with patch(
                "pr_agent.config_loader.get_settings",
                return_value=settings,
            ):
                postgres_provider.apply_automation_config_to_settings()

        settings.set.assert_any_call("CONFIG.DISABLE_AUTO_FEEDBACK", True)
        settings.set.assert_any_call("GITHUB_APP.PR_COMMANDS", ["/review"])
        settings.set.assert_any_call("GITLAB.PUSH_COMMANDS", ["/describe"])
        assert not any(
            call.args[0] == "GITHUB_APP.UNKNOWN_KEY"
            for call in settings.set.call_args_list
        )


class TestEnsurePostgresConfigLoaded:
    def test_no_database_url_is_noop(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with patch.object(
            postgres_provider,
            "apply_postgres_credentials_to_config",
        ) as mock_apply:
            postgres_provider.ensure_postgres_config_loaded(ttl_seconds=0.0)
        mock_apply.assert_not_called()

    def test_invokes_apply_once_then_respects_ttl(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")

        with patch.object(
            postgres_provider,
            "apply_postgres_credentials_to_config",
        ) as mock_apply:
            postgres_provider.ensure_postgres_config_loaded(ttl_seconds=3600.0)
            assert mock_apply.call_count == 1

            postgres_provider.ensure_postgres_config_loaded(ttl_seconds=3600.0)
            assert mock_apply.call_count == 1

    def test_invalidate_forces_reload(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")

        with patch.object(
            postgres_provider,
            "apply_postgres_credentials_to_config",
        ) as mock_apply:
            postgres_provider.ensure_postgres_config_loaded(ttl_seconds=3600.0)
            postgres_provider.invalidate_postgres_config_cache()
            postgres_provider.ensure_postgres_config_loaded(ttl_seconds=3600.0)
            assert mock_apply.call_count == 2
