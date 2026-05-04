from unittest.mock import MagicMock

import pytest

from pr_agent.servers import github_app


def _settings(values):
    class _FakeSettings:
        def get(self, key, default=None):
            return values.get(key, default)

    return _FakeSettings()


def test_get_comment_api_url_prefers_issue_pull_request_url():
    body = {"issue": {"pull_request": {"url": "https://api.github.com/repos/acme/repo/pulls/1"}}}

    assert github_app._get_comment_api_url(body) == "https://api.github.com/repos/acme/repo/pulls/1"


def test_should_capture_learning_requires_mention_when_configured(monkeypatch):
    monkeypatch.setattr(
        github_app,
        "get_settings",
        lambda: _settings(
            {
                "knowledge_base.enabled": True,
                "knowledge_base.capture_from_pr_comments": True,
                "knowledge_base.require_agent_mention": True,
                "github.app_name": "pr-agent",
            }
        ),
    )

    assert github_app._should_capture_learning("@pr-agent we prefer explicit interfaces") is True
    assert github_app._should_capture_learning("we prefer explicit interfaces") is False


@pytest.mark.asyncio
async def test_capture_repo_learning_stores_and_acknowledges(monkeypatch):
    provider = MagicMock()
    provider.repo = "acme/repo"
    provider.publish_comment = MagicMock()

    memory_provider = MagicMock()
    memory_provider.is_enabled.return_value = True
    memory_provider.store_learning.return_value = True

    monkeypatch.setattr(
        github_app,
        "get_settings",
        lambda: _settings(
            {
                "github.app_name": "pr-agent",
                "knowledge_base.enabled": True,
                "knowledge_base.capture_from_pr_comments": True,
                "knowledge_base.require_agent_mention": True,
            }
        ),
    )
    monkeypatch.setattr(github_app, "_should_capture_learning", lambda _: True)
    monkeypatch.setattr(
        github_app,
        "extract_learning_candidate",
        lambda comment_body, app_name: "We prefer explicit interfaces in this repo.",
    )
    monkeypatch.setattr(github_app, "get_git_provider_with_context", lambda pr_url: provider)
    monkeypatch.setattr(github_app, "get_memory_provider", lambda: memory_provider)

    body = {
        "sender": {"login": "reviewer-user"},
        "repository": {"full_name": "acme/repo"},
        "issue": {"number": 123},
        "comment": {
            "id": 45,
            "in_reply_to_id": None,
            "pull_request_url": "https://api.github.com/repos/acme/repo/pulls/123",
            "path": "src/app.py",
        },
    }

    await github_app._capture_repo_learning(
        body,
        "https://api.github.com/repos/acme/repo/pulls/123",
        "@pr-agent we prefer explicit interfaces",
    )

    memory_provider.store_learning.assert_called_once()
    args, kwargs = memory_provider.store_learning.call_args
    assert args[0] == "acme/repo"
    assert "explicit interfaces" in args[1]
    assert kwargs["metadata"]["source_type"] == "review_comment"
    assert kwargs["metadata"]["file_path"] == "src/app.py"
    provider.publish_comment.assert_called_once()
