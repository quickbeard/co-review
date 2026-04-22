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
        embedding_model = kb_cfg.get("embedding_model", "text-embedding-3-small")
        embedding_dimensions = kb_cfg.get("embedding_dimensions")

        # Route Mem0's OpenAI LLM + embedder through whatever OpenAI-compatible
        # gateway pr-agent itself is using. Without this Mem0 falls back to
        # https://api.openai.com and immediately 401s on custom gateway keys
        # (e.g. VTN Watson). Precedence mirrors how pr-agent resolves the URL
        # elsewhere: explicit knowledge_base override > [openai].api_base in
        # secrets > OPENAI_BASE_URL / OPENAI_API_BASE env vars.
        openai_base_url = (
            kb_cfg.get("embedding_base_url")
            or get_settings().get("openai.api_base")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("OPENAI_API_BASE")
            or None
        )

        # Mem0 drives its own LLM for fact-extraction and memory-merging. That
        # call hits the gateway over the raw OpenAI SDK, so the main pr-agent
        # model (config.model) is often the wrong pick - e.g. VTN Watson's
        # allowlist includes "openai/gpt-oss-120b:netmind" but not the
        # unprefixed "MiniMax" you might review with. Keep them decoupled.
        llm_model = (
            kb_cfg.get("llm_model")
            or get_settings().get("config.model", "")
            or "gpt-4o-mini"
        )

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
            llm_cfg: dict[str, Any] = {
                "api_key": api_key,
                "model": llm_model,
            }
            embedder_cfg: dict[str, Any] = {
                "api_key": api_key,
                "model": embedding_model,
            }
            if openai_base_url:
                llm_cfg["openai_base_url"] = openai_base_url
                embedder_cfg["openai_base_url"] = openai_base_url

            if embedding_dimensions not in (None, "", 0, "0"):
                try:
                    dimensions_value = int(embedding_dimensions)
                    if dimensions_value > 0:
                        embedder_cfg["embedding_dims"] = dimensions_value
                except (TypeError, ValueError):
                    get_logger().warning(
                        "Ignoring invalid knowledge_base.embedding_dimensions value: "
                        f"{embedding_dimensions!r}. Expected a positive integer."
                    )

            config["llm"] = {"provider": "openai", "config": llm_cfg}
            config["embedder"] = {"provider": "openai", "config": embedder_cfg}

        try:
            self._client = Memory.from_config(config)
            gateway_hint = openai_base_url or "api.openai.com (default)"
            get_logger().info(
                "Initialized Mem0 learnings provider "
                f"(collection='{collection_name}', embedder='{embedding_model}', "
                f"llm='{llm_model}', gateway='{gateway_hint}')"
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

        Return value:
            * mem0 memory id (``str``) when the record was stored.
            * ``None`` when the store failed (raised or Mem0 dropped the
              input). A previous revision returned ``""`` in the "Mem0
              accepted but emitted no id" case, which callers then treated
              as failure anyway - we normalise to ``None`` so the dashboard
              / ``/learn`` ack path can distinguish "stored" from "not
              stored" cleanly.

        We pass ``infer=False`` so Mem0 stores the text verbatim instead of
        running its internal fact-extraction LLM. That matches stage 1's
        design ("capture raw, refine later") and prevents Mem0 from silently
        dropping low-signal inputs like ``/learn trash comment lol`` - the
        Stage-2 worker is the only component allowed to touch the LLM for
        learning content.
        """
        if not self._client or not learning_text:
            return None

        meta = dict(metadata or {})
        meta["repo"] = repo_full_name
        meta.setdefault("status", "raw")
        meta["created_at"] = datetime.now(timezone.utc).isoformat()

        scope = self._repo_scope(repo_full_name)
        try:
            # mem0 uses user_id as a scope key; we map it to repository scope.
            response = self._client.add(
                learning_text,
                user_id=scope,
                metadata=meta,
                infer=False,
            )
        except TypeError:
            # Older mem0 releases didn't expose ``infer``. Fall back to the
            # default behaviour and accept the upfront LLM pass on those
            # versions rather than failing the whole store.
            try:
                response = self._client.add(
                    learning_text, user_id=scope, metadata=meta
                )
            except Exception as e:
                get_logger().warning(f"Failed to store learning in Mem0: {e}")
                return None
        except Exception as e:
            get_logger().warning(f"Failed to store learning in Mem0: {e}")
            return None

        memory_id = self._extract_memory_id(response)
        if not memory_id:
            # Mem0 succeeded without surfacing an id. Shouldn't happen with
            # ``infer=False`` but stays visible if it ever does.
            get_logger().warning(
                "Mem0 add() returned no memory id for learning; "
                f"response_shape={type(response).__name__}"
            )
            return None
        return memory_id

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
        metadata = item.get("metadata", {}) or {}
        # mem0's high-level API surfaces memory text on the top-level `memory`
        # key. When we drop to the Chroma vector_store directly (the only way
        # to list memories unscoped in modern mem0) the text lives in
        # metadata["data"] instead, so fall through to that.
        text = (
            item.get("memory")
            or item.get("text")
            or item.get("content")
            or metadata.get("data")
            or ""
        )
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
            user_id = item.get("user_id") or metadata.get("user_id") or ""
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
        """List stored learnings, optionally filtered by repo.

        Modern mem0 (>=0.1.x) changed ``Memory.get_all`` to require entity
        filters (``filters={"user_id": ...}``) and rejects the old ``user_id=``
        kwarg, so we support both shapes. When no repo is provided we fall
        back to the underlying Chroma ``vector_store.list`` - the only way
        to get an unscoped dump in the new API.
        """
        if not self._client:
            return []

        raw_items: list[dict[str, Any]] = []

        if repo_full_name:
            scope = self._repo_scope(repo_full_name)
            raw_items = self._get_all_scoped(scope, limit)
        else:
            raw_items = self._list_unscoped(limit)

        normalized = [self._normalize_item(item) for item in raw_items]
        # Sort newest first when timestamps are available.
        normalized.sort(
            key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return normalized[:limit]

    def _get_all_scoped(self, scope: str, limit: int) -> list[dict[str, Any]]:
        """Fetch records for a single user_id scope via Mem0's public API.

        Tries the modern ``filters=/top_k=`` signature first, then falls back
        to the pre-1.0 ``user_id=/limit=`` kwargs for older installs. Raw
        Chroma fallback covers the rare case where both signatures raise
        (e.g. an unsupported ``Memory.get_all`` stub).
        """
        client = self._client
        assert client is not None

        try:
            results = client.get_all(filters={"user_id": scope}, top_k=limit)
        except TypeError:
            try:
                results = client.get_all(user_id=scope, limit=limit)
            except TypeError:
                try:
                    results = client.get_all(user_id=scope)
                except Exception as e:
                    get_logger().warning(f"Failed to list Mem0 learnings (scoped): {e}")
                    return self._list_via_vector_store({"user_id": scope}, limit)
            except Exception as e:
                get_logger().warning(f"Failed to list Mem0 learnings (scoped): {e}")
                return self._list_via_vector_store({"user_id": scope}, limit)
        except Exception as e:
            get_logger().warning(f"Failed to list Mem0 learnings (scoped): {e}")
            return self._list_via_vector_store({"user_id": scope}, limit)

        if isinstance(results, dict):
            results = results.get("results") or []
        return list(results or [])

    def _list_unscoped(self, limit: int) -> list[dict[str, Any]]:
        """Dump every memory in the store, regardless of user_id scope.

        Modern mem0 refuses ``get_all`` without an entity filter, so we reach
        past it into the vector store. We still try the public API first for
        older installs that tolerate the unscoped call.
        """
        client = self._client
        assert client is not None

        try:
            results = client.get_all(top_k=limit)
            if isinstance(results, dict):
                results = results.get("results") or []
            if results:
                return list(results)
        except (TypeError, ValueError):
            pass  # modern mem0 path - drop to vector store below
        except Exception as e:
            get_logger().debug(
                f"mem0.get_all() unscoped call failed, falling back to vector_store: {e}"
            )

        return self._list_via_vector_store(None, limit)

    def _list_via_vector_store(
        self,
        filters: dict[str, Any] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Read directly from the Chroma vector store backing Mem0.

        Mem0 stores the memory text inside ``metadata["data"]`` rather than
        Chroma's ``documents`` field, so the shape we return here mimics the
        high-level API's output closely enough for ``_normalize_item`` to
        consume it unchanged.
        """
        client = self._client
        assert client is not None

        vector_store = getattr(client, "vector_store", None)
        if vector_store is None:
            get_logger().warning(
                "mem0 Memory client has no vector_store attribute; cannot list learnings."
            )
            return []

        try:
            raw = vector_store.list(filters=filters, top_k=limit)
        except Exception as e:
            get_logger().warning(f"Failed to list Mem0 learnings via vector store: {e}")
            return []

        # ChromaDB.list wraps its result in a single-element list.
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            raw = raw[0]

        items: list[dict[str, Any]] = []
        for entry in raw or []:
            payload = getattr(entry, "payload", None)
            if payload is None and isinstance(entry, dict):
                payload = entry.get("payload")
            payload = payload or {}
            entry_id = getattr(entry, "id", None)
            if entry_id is None and isinstance(entry, dict):
                entry_id = entry.get("id")
            items.append(
                {
                    "id": entry_id,
                    "memory": payload.get("data"),
                    "metadata": payload,
                    "user_id": payload.get("user_id"),
                    "created_at": payload.get("created_at"),
                }
            )
        return items

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
