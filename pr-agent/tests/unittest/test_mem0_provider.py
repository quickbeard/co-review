from types import SimpleNamespace
from unittest.mock import MagicMock

from pr_agent.memory_providers.base import LearningRecord
from pr_agent.memory_providers.mem0_provider import Mem0MemoryProvider


def _settings(values):
    class _FakeSettings:
        def get(self, key, default=None):
            return values.get(key, default)

    return _FakeSettings()


def test_init_disables_provider_when_knowledge_base_is_disabled(monkeypatch):
    monkeypatch.setattr(
        "pr_agent.memory_providers.mem0_provider.get_settings",
        lambda: _settings({"knowledge_base.enabled": False}),
    )

    provider = Mem0MemoryProvider()

    assert provider.is_enabled() is False
    assert provider._disabled_reason == "knowledge_base.disabled"


def test_store_learning_adds_repo_metadata_and_scope():
    provider = Mem0MemoryProvider.__new__(Mem0MemoryProvider)
    provider._client = MagicMock()

    stored = provider.store_learning("Org/Repo", "We prefer explicit interfaces.", metadata={"source": "test"})

    assert stored is True
    provider._client.add.assert_called_once()
    _, kwargs = provider._client.add.call_args
    assert kwargs["user_id"] == "repo:org/repo"
    assert kwargs["metadata"]["repo"] == "Org/Repo"
    assert kwargs["metadata"]["source"] == "test"
    assert isinstance(kwargs["metadata"]["created_at"], str)


def test_store_learning_returns_false_on_client_error():
    provider = Mem0MemoryProvider.__new__(Mem0MemoryProvider)
    provider._client = MagicMock()
    provider._client.add.side_effect = RuntimeError("failed")

    assert provider.store_learning("org/repo", "text") is False


def test_get_repo_learnings_normalizes_result_fields():
    provider = Mem0MemoryProvider.__new__(Mem0MemoryProvider)
    provider._client = MagicMock()
    provider._client.search.return_value = [
        {
            "memory": "Prefer explicit typing",
            "score": 0.91,
            "metadata": {"created_at": "2026-01-01T10:00:00Z"},
        },
        {
            "text": "Second preference",
            "score": 0.5,
            "metadata": {},
        },
        {
            "content": "Fallback content field",
            "metadata": {"created_at": "invalid"},
        },
    ]

    learnings = provider.get_repo_learnings("Org/Repo", "query", limit=3)

    assert len(learnings) == 3
    assert all(isinstance(item, LearningRecord) for item in learnings)
    assert learnings[0].text == "Prefer explicit typing"
    assert learnings[0].created_at is not None
    assert learnings[1].text == "Second preference"
    assert learnings[2].text == "Fallback content field"
    provider._client.search.assert_called_once_with("query", user_id="repo:org/repo", limit=3)


def test_get_repo_learnings_returns_empty_on_search_error():
    provider = Mem0MemoryProvider.__new__(Mem0MemoryProvider)
    provider._client = MagicMock()
    provider._client.search.side_effect = RuntimeError("boom")

    learnings = provider.get_repo_learnings("org/repo", "query")

    assert learnings == []
