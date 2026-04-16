from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class LearningRecord:
    text: str
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
