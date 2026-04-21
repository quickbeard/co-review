from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class LearningRecord:
    text: str
    id: str | None = None
    repo: str | None = None
    score: float | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryProvider(Protocol):
    def is_enabled(self) -> bool:
        ...

    def store_learning(
        self,
        repo_full_name: str,
        learning_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        ...

    def get_repo_learnings(
        self,
        repo_full_name: str,
        query_text: str,
        limit: int = 5,
    ) -> list[LearningRecord]:
        ...

    def list_all_learnings(
        self,
        repo_full_name: str | None = None,
        limit: int = 100,
    ) -> list[LearningRecord]:
        ...

    def delete_learning(self, learning_id: str) -> bool:
        ...

    def list_repos(self) -> list[str]:
        ...
