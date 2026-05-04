import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from pr_agent.memory_providers.base import LearningRecord
from pr_agent.tools.pr_reviewer import PRReviewer


def _settings(values):
    class _FakeSettings:
        def get(self, key, default=None):
            return values.get(key, default)

    return _FakeSettings()


def test_get_repo_full_name_prefers_provider_repo():
    reviewer = PRReviewer.__new__(PRReviewer)
    reviewer.git_provider = SimpleNamespace(repo="acme/repo")
    reviewer.pr_url = "https://api.github.com/repos/ignored/ignored/pulls/1"

    assert reviewer._get_repo_full_name() == "acme/repo"


def test_get_repo_full_name_falls_back_to_pr_url():
    reviewer = PRReviewer.__new__(PRReviewer)
    reviewer.git_provider = SimpleNamespace(repo="")
    reviewer.pr_url = "https://api.github.com/repos/acme/repo/pulls/12"

    assert reviewer._get_repo_full_name() == "acme/repo"


def test_summarize_repo_learnings_orders_by_recency():
    older = LearningRecord(text="Older guidance", created_at=datetime.datetime(2025, 1, 1))
    newer = LearningRecord(text="Newer guidance", created_at=datetime.datetime(2026, 1, 1))

    summary = PRReviewer._summarize_repo_learnings([older, newer], max_items=2, max_chars=200)

    assert summary.splitlines() == ["- Newer guidance", "- Older guidance"]


def test_apply_repository_learnings_updates_prompt_vars(monkeypatch):
    reviewer = PRReviewer.__new__(PRReviewer)
    reviewer.git_provider = SimpleNamespace(repo="acme/repo", pr=SimpleNamespace(title="Improve reviewer memory"))
    reviewer.pr_url = "https://api.github.com/repos/acme/repo/pulls/12"
    reviewer.pr_description = "This PR improves memory injection."
    reviewer.vars = {
        "commit_messages_str": "feat: add memory integration",
        "repo_learnings_summary": "",
        "repo_learnings_count": 0,
    }
    reviewer.token_handler = None
    reviewer._create_token_handler = MagicMock(return_value="new-token-handler")

    memory_provider = MagicMock()
    memory_provider.is_enabled.return_value = True
    memory_provider.get_repo_learnings.return_value = [
        LearningRecord(text="We prefer direct language in review comments.", created_at=datetime.datetime(2026, 1, 1)),
        LearningRecord(text="In this repo we avoid vague TODOs.", created_at=datetime.datetime(2025, 12, 1)),
    ]

    monkeypatch.setattr(
        "pr_agent.tools.pr_reviewer.get_settings",
        lambda: _settings(
            {
                "knowledge_base.enabled": True,
                "knowledge_base.apply_to_review": True,
                "knowledge_base.max_retrieved_learnings": 5,
                "knowledge_base.max_summary_chars": 500,
            }
        ),
    )
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.get_memory_provider", lambda: memory_provider)

    reviewer._apply_repository_learnings()

    assert reviewer.vars["repo_learnings_count"] == 2
    assert reviewer.vars["repo_learnings_summary"].startswith("- We prefer direct language")
    assert reviewer.token_handler == "new-token-handler"
    memory_provider.get_repo_learnings.assert_called_once()
