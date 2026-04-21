"""`/learn` command tool.

Captures explicit user-provided learnings posted as PR comments into the
knowledge base. Three input patterns are supported:

1. Inline text:       ``/learn We prefer typed signatures for public helpers.``
2. Review-thread text: ``/learn`` posted as a reply - parent comment body is
   used as the learning text.
3. Repeat of self:     ``/learn`` alone on an issue comment where the comment
   author included the preference text in the same comment before the
   command (rare; handled by pattern 1 if they wrap the text with the
   command). For pattern 2, the parent fetch covers the common case.

Design notes for stage 1:

* Enabled by default (``knowledge_base.explicit_learn_enabled = true``).
  Administrators can disable it from the Dashboard; re-enabling it after a
  disable will eventually require a ruleset, but that UX is a follow-up.
* The command is treated as a trusted signal - whatever non-empty text the
  reviewer provides is stored verbatim with ``status="raw"``. A background
  refinement worker (stage 2) polishes the wording before reviews use it.
* Dashboard blurs raw entries until refinement completes.
"""
from __future__ import annotations

from functools import partial
from typing import Any

from pr_agent.algo.ai_handlers.base_ai_handler import BaseAiHandler
from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
from pr_agent.algo.learning_extractor import extract_explicit_learning
from pr_agent.config_loader import get_settings
from pr_agent.git_providers import get_git_provider_with_context
from pr_agent.log import get_logger
from pr_agent.memory_providers import get_memory_provider


class PRLearn:
    """Handle the ``/learn`` slash command for explicit KB capture."""

    def __init__(
        self,
        pr_url: str,
        args: list[str] | None = None,
        ai_handler: partial[BaseAiHandler,] | None = LiteLLMAIHandler,
    ) -> None:
        self.pr_url = pr_url
        self.args = args or []
        # ``ai_handler`` is accepted for interface parity with other tools but
        # stage 1 does not call the LLM. Keeping it in the signature lets us
        # opt in later without changing the dispatcher.
        self._ai_handler_ctor = ai_handler
        self.git_provider = get_git_provider_with_context(pr_url)
        self._learn_context: dict[str, Any] = dict(
            get_settings().get("learn_context", {}) or {}
        )

    # ------------------------------------------------------------------ helpers

    def _candidate_text(self) -> tuple[str, str]:
        """Return ``(candidate, source)`` - the raw text to learn from.

        ``source`` is one of ``"inline"``, ``"parent_comment"``, ``"empty"``
        and is stored in metadata so the dashboard can distinguish shapes.
        """
        raw_body = (self._learn_context.get("raw_comment_body") or "").strip()
        command_token = get_settings().get(
            "knowledge_base.learn_command", "/learn"
        )

        if raw_body:
            stripped = raw_body
            if stripped.lower().startswith(command_token.lower()):
                stripped = stripped[len(command_token):].lstrip(" :,-").strip()
            if stripped:
                return stripped, "inline"

        # Fallback for shell-parsed args (posix shlex preserves words only).
        joined = " ".join(self.args).strip()
        if joined:
            return joined, "inline"

        # No inline text => try the parent comment in a review thread.
        parent_id = self._learn_context.get("parent_comment_id")
        if parent_id and hasattr(self.git_provider, "get_review_thread_comments"):
            try:
                thread = self.git_provider.get_review_thread_comments(parent_id)
            except Exception as e:  # defensive: never crash the command
                get_logger().warning(
                    f"Failed to fetch parent review comment for /learn: {e}"
                )
                thread = []
            parent = next(
                (c for c in thread if getattr(c, "id", None) == parent_id),
                None,
            )
            parent_body = getattr(parent, "body", "") if parent else ""
            if parent_body:
                return parent_body.strip(), "parent_comment"

        return "", "empty"

    def _publish(self, message: str) -> None:
        if get_settings().get("config.publish_output", True):
            try:
                self.git_provider.publish_comment(message)
            except Exception:
                get_logger().warning(
                    "Failed to publish /learn acknowledgment comment"
                )

    def _repo_full_name(self) -> str:
        return (
            getattr(self.git_provider, "repo", "")
            or self._learn_context.get("repo_full_name", "")
            or ""
        )

    # ---------------------------------------------------------------------- run

    async def run(self) -> None:
        settings = get_settings()

        if not settings.get("knowledge_base.enabled", False):
            get_logger().info(
                "/learn invoked but knowledge_base.enabled is false; ignoring."
            )
            return

        if not settings.get("knowledge_base.explicit_learn_enabled", False):
            self._publish(
                "`/learn` is currently disabled for this installation. "
                "An administrator can enable it by setting "
                "`knowledge_base.explicit_learn_enabled = true` in the "
                "Dashboard configuration."
            )
            return

        candidate, source = self._candidate_text()
        if not candidate:
            self._publish(
                "I could not find any learning text in your comment. "
                "Either post the preference with the command "
                "(`/learn We prefer X over Y ...`) or reply `/learn` to a "
                "comment that already contains the preference."
            )
            return

        # ``extract_explicit_learning`` only strips the optional command
        # token and rejects empty strings - it does not filter by content.
        learning_text = extract_explicit_learning(
            candidate,
            command_token=settings.get("knowledge_base.learn_command", "/learn"),
        )

        if not learning_text:
            # Reached only if the candidate collapses to an empty string
            # after stripping the command token (e.g. ``/learn   ``).
            self._publish(
                "I could not find any learning text in your comment. "
                "Please post the preference with the command "
                "(`/learn We prefer X over Y ...`) or reply `/learn` to a "
                "comment that already contains the preference."
            )
            return

        repo_full_name = self._repo_full_name()
        if not repo_full_name:
            get_logger().warning(
                "/learn could not determine repository full name; skipping store."
            )
            self._publish(
                "I could not resolve the repository for this PR, so the "
                "learning was not stored. Please try again."
            )
            return

        memory_provider = get_memory_provider()
        if not memory_provider.is_enabled():
            self._publish(
                "The knowledge base is not available right now, so I could "
                "not store your learning. Please retry later."
            )
            return

        metadata: dict[str, Any] = {
            "source_type": "explicit_learn",
            "trigger": "slash_command",
            "status": "raw",
            "raw_comment": candidate,
            "refined_text": None,
            "refine_attempts": 0,
            "last_refine_error": None,
            "candidate_source": source,
            "pr_number": self._learn_context.get("pr_number"),
            "comment_id": self._learn_context.get("comment_id"),
            "parent_comment_id": self._learn_context.get("parent_comment_id"),
            "created_by": self._learn_context.get("sender_login"),
            "repo": repo_full_name,
        }
        file_path = self._learn_context.get("file_path")
        if file_path:
            metadata["file_path"] = file_path

        stored_id = memory_provider.store_learning(
            repo_full_name, learning_text, metadata=metadata
        )
        if not stored_id:
            self._publish(
                "I could not store your learning due to an internal error. "
                "Please check the server logs or try again later."
            )
            return

        ack_lines = [
            "Learning captured:",
            f"> {learning_text}",
            "",
            "I stored this as a **raw** entry - a background job will refine "
            "the wording before it is applied to future reviews. You can "
            "manage stored learnings from the Dashboard.",
        ]
        self._publish("\n".join(ack_lines))
        get_logger().info(
            "Stored explicit /learn entry",
            extra={
                "repo": repo_full_name,
                "learning_id": stored_id if isinstance(stored_id, str) else None,
                "pr_number": metadata.get("pr_number"),
                "created_by": metadata.get("created_by"),
            },
        )
