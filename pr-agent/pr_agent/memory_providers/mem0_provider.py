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
    ) -> bool:
        if not self._client or not learning_text:
            return False

        meta = dict(metadata or {})
        meta["repo"] = repo_full_name
        meta["created_at"] = datetime.now(timezone.utc).isoformat()

        scope = self._repo_scope(repo_full_name)
        try:
            # mem0 uses user_id as a scope key; we map it to repository scope.
            self._client.add(learning_text, user_id=scope, metadata=meta)
            return True
        except Exception as e:
            get_logger().warning(f"Failed to store learning in Mem0: {e}")
            return False

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
