from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger
from pr_agent.memory_providers.base import LearningRecord


class Mem0MemoryProvider:
    def __init__(self):
        self._client = None
        self._disabled_reason = ""
        self._initialize()

    def _initialize(self):
        if not get_settings().get("knowledge_base.enabled", False):
            self._disabled_reason = "knowledge_base.disabled"
            return

        provider_name = get_settings().get("knowledge_base.provider", "mem0")
        if provider_name != "mem0":
            self._disabled_reason = f"provider_not_supported:{provider_name}"
            return

        try:
            from mem0 import Memory
        except Exception as e:
            self._disabled_reason = "mem0_import_failed"
            get_logger().warning(f"Mem0 import failed, learnings disabled: {e}")
            return

        kb_cfg = get_settings().get("knowledge_base", {})
        chroma_path = kb_cfg.get("chroma_path", "./.mem0/chroma")
        collection_name = kb_cfg.get("collection_name", "pr_agent_repo_learnings")

        api_key = os.environ.get("OPENAI_API_KEY", get_settings().get("openai.key", ""))
        # embedding_model = kb_cfg.get("embedding_model", "text-embedding-3-small")
        embedding_model = "BAAI/bge-m3"
        embedding_dimensions = kb_cfg.get("embedding_dimensions")

        config: dict[str, Any] = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": collection_name,
                    "path": chroma_path,
                },
            },
        }

        if api_key:
            config["llm"] = {
                "provider": "openai",
                "config": {
                    "api_key": api_key,
                    "model": get_settings().get("config.model", ""),
                },
            }
            config["embedder"] = {
                "provider": "openai",
                "config": {
                    "api_key": api_key,
                    "model": embedding_model,
                },
            }
            if embedding_dimensions not in (None, "", 0, "0"):
                try:
                    dimensions_value = int(embedding_dimensions)
                    if dimensions_value > 0:
                        config["embedder"]["config"]["embedding_dims"] = dimensions_value
                except (TypeError, ValueError):
                    get_logger().warning(
                        "Ignoring invalid knowledge_base.embedding_dimensions value: "
                        f"{embedding_dimensions!r}. Expected a positive integer."
                    )

        try:
            config["embedder"]["config"]["embedding_dims"] = None
            self._client = Memory.from_config(config)
            get_logger().info(
                f"Initialized Mem0 learnings provider with Chroma collection '{collection_name}'"
            )
        except Exception as e:
            self._disabled_reason = "mem0_init_failed"
            self._client = None
            get_logger().warning(f"Failed to initialize Mem0 provider: {e}")

    def is_enabled(self) -> bool:
        return self._client is not None

    @staticmethod
    def _repo_scope(repo_full_name: str) -> str:
        return f"repo:{repo_full_name.lower().strip()}"

    def store_learning(
        self,
        repo_full_name: str,
        learning_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Persist a learning and return the mem0 memory id on success.

        Return value shape changed from ``bool`` to ``str | None`` so the
        caller (e.g. the ``/learn`` tool) can reference the stored record in
        the acknowledgement message and so a future refinement worker can
        look it up. A non-empty string denotes success; ``None`` means the
        store failed. Callers doing a truthy check keep working unchanged.
        """
        if not self._client or not learning_text:
            return None

        meta = dict(metadata or {})
        meta["repo"] = repo_full_name
        meta.setdefault("status", "refined")
        meta["created_at"] = datetime.now(timezone.utc).isoformat()

        scope = self._repo_scope(repo_full_name)
        try:
            # mem0 uses user_id as a scope key; we map it to repository scope.
            response = self._client.add(learning_text, user_id=scope, metadata=meta)
        except Exception as e:
            get_logger().warning(f"Failed to store learning in Mem0: {e}")
            return None

        memory_id = self._extract_memory_id(response)
        return memory_id or ""  # empty string is still truthy-enough sentinel

    @staticmethod
    def _extract_memory_id(response: Any) -> str | None:
        """Best-effort extraction of the memory id from a mem0 ``add`` result.

        mem0's return shape varies across versions - sometimes a dict with
        ``results``, sometimes a raw list, sometimes a single dict. We walk
        the common shapes and return the first id we can find. Failures are
        non-fatal because the caller only needs the id for UX.
        """
        if not response:
            return None
        try:
            candidates: list[Any] = []
            if isinstance(response, dict):
                results = response.get("results")
                if isinstance(results, list):
                    candidates.extend(results)
                elif "id" in response:
                    candidates.append(response)
            elif isinstance(response, list):
                candidates.extend(response)
            for item in candidates:
                if isinstance(item, dict) and item.get("id"):
                    return str(item["id"])
        except Exception:  # defensive
            return None
        return None

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> LearningRecord:
        text = (
            item.get("memory")
            or item.get("text")
            or item.get("content")
            or ""
        )
        metadata = item.get("metadata", {}) or {}
        created_at = None
        # Prefer mem0's top-level created_at, fall back to metadata
        created_raw = item.get("created_at") or metadata.get("created_at")
        if isinstance(created_raw, str):
            try:
                created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except Exception:
                created_at = None

        repo = metadata.get("repo")
        if not repo:
            # derive from user_id scope (e.g. "repo:org/name")
            user_id = item.get("user_id", "")
            if isinstance(user_id, str) and user_id.startswith("repo:"):
                repo = user_id[len("repo:"):]

        return LearningRecord(
            text=text,
            id=item.get("id"),
            repo=repo,
            score=item.get("score"),
            created_at=created_at,
            metadata=metadata,
        )

    def get_repo_learnings(
        self,
        repo_full_name: str,
        query_text: str,
        limit: int = 5,
    ) -> list[LearningRecord]:
        if not self._client:
            return []

        scope = self._repo_scope(repo_full_name)
        try:
            results = self._client.search(query_text, filters={"user_id": scope}, limit=limit)
        except Exception as e:
            get_logger().warning(f"Failed to fetch Mem0 learnings: {e}")
            return []

        # Some mem0 versions return {"results": [...]}, others return a list directly.
        if isinstance(results, dict):
            results = results.get("results") or []
        return [self._normalize_item(item) for item in (results or [])]

    def list_all_learnings(
        self,
        repo_full_name: str | None = None,
        limit: int = 100,
    ) -> list[LearningRecord]:
        if not self._client:
            return []

        try:
            if repo_full_name:
                results = self._client.get_all(
                    user_id=self._repo_scope(repo_full_name), limit=limit
                )
            else:
                results = self._client.get_all(limit=limit)
        except TypeError:
            # Older mem0 signatures may not support the `limit` kwarg.
            try:
                if repo_full_name:
                    results = self._client.get_all(user_id=self._repo_scope(repo_full_name))
                else:
                    results = self._client.get_all()
            except Exception as e:
                get_logger().warning(f"Failed to list Mem0 learnings: {e}")
                return []
        except Exception as e:
            get_logger().warning(f"Failed to list Mem0 learnings: {e}")
            return []

        if isinstance(results, dict):
            results = results.get("results") or []

        normalized = [self._normalize_item(item) for item in (results or [])]
        # Sort newest first when timestamps are available.
        normalized.sort(
            key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return normalized[:limit]

    def delete_learning(self, learning_id: str) -> bool:
        if not self._client or not learning_id:
            return False
        try:
            self._client.delete(memory_id=learning_id)
            return True
        except Exception as e:
            get_logger().warning(f"Failed to delete Mem0 learning {learning_id}: {e}")
            return False

    def list_repos(self) -> list[str]:
        if not self._client:
            return []
        records = self.list_all_learnings(limit=1000)
        repos = {r.repo for r in records if r.repo}
        return sorted(repos)

    # ------------------------------------------------------------------
    # Refinement worker interface (stage 2 consumer; stage 1 producer only)
    # ------------------------------------------------------------------

    def list_pending_refinements(
        self,
        limit: int = 50,
        max_attempts: int | None = None,
    ) -> list[LearningRecord]:
        """Return raw learnings awaiting background refinement.

        Stage 1 populates the ``status="raw"`` metadata key; the future
        refinement worker will consume records returned from here. When
        ``max_attempts`` is provided, entries whose ``refine_attempts`` meets
        or exceeds the limit are skipped so a poison record cannot stall the
        queue forever.
        """
        if not self._client:
            return []
        records = self.list_all_learnings(limit=limit * 4 if limit else 200)
        pending: list[LearningRecord] = []
        for record in records:
            meta = record.metadata or {}
            if meta.get("status") != "raw":
                continue
            if max_attempts is not None:
                attempts = int(meta.get("refine_attempts") or 0)
                if attempts >= max_attempts:
                    continue
            pending.append(record)
            if limit and len(pending) >= limit:
                break
        return pending

    def update_learning_after_refinement(
        self,
        learning_id: str,
        *,
        refined_text: str | None,
        status: str,
        error: str | None = None,
    ) -> bool:
        """Flip a raw learning to its refined form (or mark a retry).

        The worker calls this with ``status="refined"`` plus the new text, or
        with ``status="raw"`` and an ``error`` message to bump the attempts
        counter without changing the memory content.
        """
        if not self._client or not learning_id:
            return False

        try:
            existing = self._client.get(memory_id=learning_id)
        except Exception as e:
            get_logger().warning(
                f"Failed to load Mem0 learning {learning_id} for refinement: {e}"
            )
            return False

        if not existing:
            return False

        meta = dict((existing.get("metadata") or {}))
        meta["status"] = status
        meta["last_refine_error"] = error
        meta["refine_attempts"] = int(meta.get("refine_attempts") or 0) + 1
        if status == "refined" and refined_text:
            meta["refined_text"] = refined_text
            meta["last_refine_error"] = None

        new_text = refined_text if (status == "refined" and refined_text) else existing.get("memory")
        try:
            self._client.update(memory_id=learning_id, data=new_text, metadata=meta)
            return True
        except TypeError:
            # Some mem0 versions use a different kwarg for the payload.
            try:
                self._client.update(memory_id=learning_id, metadata=meta)
                return True
            except Exception as e:
                get_logger().warning(
                    f"Failed to update Mem0 learning {learning_id}: {e}"
                )
                return False
        except Exception as e:
            get_logger().warning(
                f"Failed to update Mem0 learning {learning_id}: {e}"
            )
            return False
