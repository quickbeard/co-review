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
    ) -> str | None:
        """Persist a learning. Return the storage id on success, None on failure."""
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

    def count_learnings(self, repo_full_name: str | None = None) -> int:
        """Return the total number of stored learnings (unbounded by limit).

        Used for dashboard counters where we want the true population size,
        not the page that was returned by a limited ``list_all_learnings``
        call.
        """
        ...

    def delete_learning(self, learning_id: str) -> bool:
        ...

    def list_repos(self) -> list[str]:
        ...

    def list_pending_refinements(
        self,
        limit: int = 50,
        max_attempts: int | None = None,
    ) -> list[LearningRecord]:
        """Return raw learnings awaiting background refinement.

        Implementations should filter by ``metadata.status == "raw"`` and
        exclude entries whose ``metadata.refine_attempts`` meets or exceeds
        ``max_attempts`` (when provided), so poison records cannot stall
        the queue.
        """
        ...

    def update_learning_after_refinement(
        self,
        learning_id: str,
        *,
        refined_text: str | None,
        status: str,
        error: str | None = None,
    ) -> bool:
        """Finalise or retry a refinement.

        Implementations MUST increment ``metadata.refine_attempts`` on every
        call. On ``status="refined"`` with ``refined_text``, the stored text
        is overwritten and ``last_refine_error`` cleared. On other statuses
        the stored text is left alone and ``error`` is recorded.
        """
        ...
