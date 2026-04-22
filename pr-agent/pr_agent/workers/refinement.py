"""Stage 2 background worker: refine raw learnings via LLM.

Lifecycle
---------
1. On start, pulls DB-backed config into Dynaconf so the worker uses whatever
   model / provider the Dashboard has chosen.
2. Loops forever with a poll interval. Each tick:
   - Refreshes DB-backed config via the TTL helper (so admin edits take
     effect without a restart).
   - Asks the memory provider for up to ``BATCH_SIZE`` raw learnings whose
     ``refine_attempts`` are still below ``MAX_ATTEMPTS``.
   - Runs each one through :class:`LiteLLMAIHandler` with a strict-JSON
     prompt that produces either a polished rule (``status="refined"``) or
     an explicit rejection (``status="rejected"``).
   - Records transient failures (bad JSON, network, 5xx) as a bumped
     ``refine_attempts`` + ``last_refine_error`` so the next tick retries.
3. If the LLM is rate-limited/quota-exceeded, the whole worker enters an
   exponential backoff window so we don't burn attempts on records we'd
   definitely fail to refine right now. Once quota recovers, processing
   resumes automatically.

Operational knobs are module-level constants on purpose: Stage 2 is meant to
ship with sensible defaults and no UI. The Dashboard's Knowledge Base
Refinement card has placeholder copy describing these values; when we want
to expose them we just read them from Dynaconf instead of from constants.
"""

from __future__ import annotations

import asyncio
import json
import re
import signal
import time
from dataclasses import dataclass, field
from typing import Any

# Tunables. Kept as module-level constants so they're easy to patch in
# tests and easy to promote to Dynaconf settings later.
POLL_INTERVAL_SECONDS: float = 30.0
BATCH_SIZE: int = 10
MAX_ATTEMPTS: int = 10
# Backoff ladder when the LLM reports quota/rate-limit errors. We stay at
# the final rung forever rather than giving up - the user explicitly asked
# that records auto-resume when quota recovers.
QUOTA_BACKOFF_SCHEDULE_SECONDS: tuple[int, ...] = (60, 300, 1800, 3600)

# Strict-JSON output contract. We intentionally keep the prompt tight: every
# extra token is paid for on every learning. If we find the model ignores
# the instructions we can add 1-2 few-shot examples later.
# This system prompt should also be exposed in the Dashboard as a user-editable setting.
REFINEMENT_SYSTEM_PROMPT = (
    "You normalise raw reviewer feedback into durable coding rules for a"
    " PR-review knowledge base. Return STRICT JSON and nothing else, one of"
    " these two shapes:\n"
    '  {"refined": "<concise, imperative, self-contained rule in 1-3'
    ' sentences>"}\n'
    '  {"reject": true, "reason": "<short reason this is not a codebase'
    ' preference>"}\n'
    "Reject if the input is chit-chat, a question, unrelated, or not"
    " technical guidance. Never add commentary outside the JSON."
)


@dataclass
class RefinementOutcome:
    """Result of refining a single learning record.

    Exactly one of ``refined_text`` or ``rejection_reason`` is populated on a
    terminal outcome. ``transient`` means we should bump the attempts counter
    and leave the record in ``status="raw"`` so a later tick can retry.
    ``quota`` means the LLM is rate-limited and the whole worker should back
    off (not just this one record).
    """

    refined_text: str | None = None
    rejection_reason: str | None = None
    transient: bool = False
    quota: bool = False
    error_message: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.refined_text is not None or self.rejection_reason is not None


@dataclass
class TickReport:
    """Summary of one worker iteration, used in logs and tests."""

    processed: int = 0
    refined: int = 0
    rejected: int = 0
    transient_failures: int = 0
    quota_hit: bool = False
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Quota / rate-limit detection
# =============================================================================
# We don't want to pin ``litellm.exceptions.RateLimitError`` because the
# worker needs to work with other LLM handlers too. Match by class name and
# by substring on the error message, which is the broadly-compatible approach
# used elsewhere in this repo.
_QUOTA_EXCEPTION_CLASS_NAMES: frozenset[str] = frozenset(
    {"RateLimitError", "Timeout", "APITimeoutError", "ServiceUnavailableError"}
)
_QUOTA_MESSAGE_SUBSTRINGS: tuple[str, ...] = (
    "rate limit",
    "rate_limit",
    "ratelimit",
    "quota",
    "429",
    "too many requests",
    "insufficient_quota",
)


def is_quota_error(exc: BaseException) -> bool:
    """True if the exception looks like an LLM quota / rate-limit signal.

    The worker treats these differently from generic network failures: when
    we see one, we pause the whole loop for a progressively longer window
    instead of burning attempts. See :data:`QUOTA_BACKOFF_SCHEDULE_SECONDS`.
    """
    if type(exc).__name__ in _QUOTA_EXCEPTION_CLASS_NAMES:
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
    if status == 429:
        return True
    message = str(exc).lower()
    return any(token in message for token in _QUOTA_MESSAGE_SUBSTRINGS)


# =============================================================================
# Prompt + output parsing
# =============================================================================


def build_user_prompt(record: Any) -> str:
    """Assemble the user-turn prompt from a learning record.

    Accepts anything with ``text`` and ``metadata`` attributes (duck-typed so
    tests can feed in plain namespaces without importing LearningRecord).
    """
    meta = dict(getattr(record, "metadata", None) or {})
    repo = getattr(record, "repo", None) or meta.get("repo_full_name") or "unknown repo"
    sender = meta.get("sender_login") or meta.get("author") or "unknown reviewer"
    pr_number = meta.get("pr_number")
    pr_suffix = f" PR #{pr_number}" if pr_number else ""

    # Prefer the raw_comment captured by PRLearn when present; fall back to
    # ``record.text`` so passively-captured learnings still have something.
    raw = meta.get("raw_comment") or getattr(record, "text", "") or ""
    raw = raw.strip() or "(empty comment body)"

    return (
        f'Raw PR comment from reviewer "{sender}" on {repo}{pr_suffix}:\n'
        f"---\n{raw}\n---\n"
        "Return your response as JSON only."
    )


# Matches the first `{ ... }` block in a string. Models occasionally wrap
# JSON in prose despite instructions; this salvages the intended payload.
_JSON_BLOCK_RE = re.compile(r"\{.*?\}", re.DOTALL)


def parse_llm_output(raw: str) -> RefinementOutcome:
    """Turn an LLM response string into a :class:`RefinementOutcome`.

    Any failure to parse produces a ``transient`` outcome so the next tick
    retries - we'd rather eat an extra LLM call than silently drop a record.
    """
    if not raw or not raw.strip():
        return RefinementOutcome(transient=True, error_message="empty LLM response")

    payload: dict[str, Any] | None = None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = None

    if not isinstance(payload, dict):
        return RefinementOutcome(
            transient=True,
            error_message="LLM did not return a JSON object",
        )

    if payload.get("reject") is True:
        reason = str(payload.get("reason") or "rejected without reason").strip()
        return RefinementOutcome(rejection_reason=reason or "rejected without reason")

    refined = payload.get("refined")
    if isinstance(refined, str) and refined.strip():
        return RefinementOutcome(refined_text=refined.strip())

    return RefinementOutcome(
        transient=True,
        error_message="LLM JSON had neither a valid 'refined' nor 'reject'",
    )


# =============================================================================
# Worker
# =============================================================================


class RefinementWorker:
    """Long-running consumer for raw learning records.

    Keep this class testable: the main loop in :meth:`run_forever` is a thin
    scheduler around :meth:`run_once`, which is itself a thin wrapper around
    :meth:`_refine_one`. Unit tests exercise the latter two without spinning
    the scheduler.
    """

    def __init__(
        self,
        *,
        memory_provider: Any,
        ai_handler: Any,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        batch_size: int = BATCH_SIZE,
        max_attempts: int = MAX_ATTEMPTS,
    ):
        self._memory = memory_provider
        self._ai = ai_handler
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._max_attempts = max_attempts
        # Quota backoff state. ``_quota_level`` indexes into
        # QUOTA_BACKOFF_SCHEDULE_SECONDS, clamped at the last entry.
        self._quota_level = 0
        self._quota_until: float = 0.0
        self._stopping = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_stop(self) -> None:
        """Ask the worker to exit after the current tick (used by signal handlers)."""
        self._stopping = True

    async def run_forever(self) -> None:
        """Main poll loop. Exits when :meth:`request_stop` is called."""
        from pr_agent.log import get_logger

        log = get_logger()
        log.bind(
            poll_interval_s=self._poll_interval,
            batch_size=self._batch_size,
            max_attempts=self._max_attempts,
        ).info("refinement.start")
        while not self._stopping:
            # Respect quota backoff before doing any work.
            wait_remaining = self._quota_until - time.monotonic()
            if wait_remaining > 0:
                await asyncio.sleep(min(wait_remaining, self._poll_interval))
                continue

            # Let DB-backed Dynaconf changes (model, KB toggles) take effect
            # on the next batch without a restart.
            self._refresh_settings()

            try:
                report = await self.run_once()
            except Exception as exc:  # pragma: no cover - last-resort shield
                log.exception(f"refinement.tick_crashed: {exc}")
                report = TickReport(errors=[str(exc)])

            log.bind(
                processed=report.processed,
                refined=report.refined,
                rejected=report.rejected,
                transient_failures=report.transient_failures,
                quota_hit=report.quota_hit,
            ).info("refinement.tick")

            await asyncio.sleep(self._poll_interval)

        log.info("refinement.stop")

    async def run_once(self) -> TickReport:
        """Process one batch. Returns a structured report for logs and tests."""
        report = TickReport()

        if not self._memory or not getattr(self._memory, "is_enabled", lambda: False)():
            # Knowledge base disabled: no-op. Avoid log spam by staying quiet.
            return report

        try:
            pending = self._memory.list_pending_refinements(
                limit=self._batch_size,
                max_attempts=self._max_attempts,
            )
        except Exception as exc:
            report.errors.append(f"list_pending_refinements failed: {exc}")
            return report

        for record in pending:
            if self._stopping or self._quota_until > time.monotonic():
                break
            report.processed += 1
            learning_id = getattr(record, "id", None)
            if not learning_id:
                report.transient_failures += 1
                report.errors.append("record without id; skipped")
                continue

            outcome = await self._refine_one(record)

            if outcome.quota:
                self._note_quota_hit()
                report.quota_hit = True
                # Count as transient so the visible metric matches reality.
                report.transient_failures += 1
                self._safe_update(
                    learning_id,
                    refined_text=None,
                    status="raw",
                    error=outcome.error_message or "quota",
                )
                break  # drop the rest of the batch; resume after backoff

            if outcome.refined_text:
                ok = self._safe_update(
                    learning_id,
                    refined_text=outcome.refined_text,
                    status="refined",
                    error=None,
                )
                if ok:
                    report.refined += 1
                    self._reset_quota_backoff()
                else:
                    report.errors.append(f"update failed for {learning_id}")
                continue

            if outcome.rejection_reason:
                ok = self._safe_update(
                    learning_id,
                    refined_text=None,
                    status="rejected",
                    error=outcome.rejection_reason,
                )
                if ok:
                    report.rejected += 1
                    self._reset_quota_backoff()
                else:
                    report.errors.append(f"update failed for {learning_id}")
                continue

            # Transient failure path: bump attempts so the record eventually
            # hits MAX_ATTEMPTS if the LLM keeps failing on it, but leave the
            # status as raw so the next tick retries.
            report.transient_failures += 1
            self._safe_update(
                learning_id,
                refined_text=None,
                status="raw",
                error=outcome.error_message or "transient failure",
            )

        return report

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _refine_one(self, record: Any) -> RefinementOutcome:
        """Call the LLM for one record and classify the outcome."""
        from pr_agent.config_loader import get_settings

        model = get_settings().get("config.model", "gpt-4o-mini")
        temperature = float(get_settings().get("config.temperature", 0.2) or 0.2)
        user_prompt = build_user_prompt(record)

        try:
            response, _finish = await self._ai.chat_completion(
                model=model,
                system=REFINEMENT_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=temperature,
            )
        except Exception as exc:
            if is_quota_error(exc):
                return RefinementOutcome(quota=True, error_message=str(exc)[:500])
            return RefinementOutcome(transient=True, error_message=str(exc)[:500])

        if not isinstance(response, str):
            response = str(response or "")
        return parse_llm_output(response)

    def _safe_update(
        self,
        learning_id: str,
        *,
        refined_text: str | None,
        status: str,
        error: str | None,
    ) -> bool:
        """Call ``update_learning_after_refinement`` and swallow its errors.

        The provider already logs internally; we just want to keep the tick
        loop alive regardless of the mem0 client state.
        """
        try:
            return bool(
                self._memory.update_learning_after_refinement(
                    learning_id,
                    refined_text=refined_text,
                    status=status,
                    error=error,
                )
            )
        except Exception:
            return False

    def _note_quota_hit(self) -> None:
        """Extend the quota backoff window using the ladder."""
        delay = QUOTA_BACKOFF_SCHEDULE_SECONDS[
            min(self._quota_level, len(QUOTA_BACKOFF_SCHEDULE_SECONDS) - 1)
        ]
        self._quota_until = time.monotonic() + delay
        self._quota_level = min(
            self._quota_level + 1, len(QUOTA_BACKOFF_SCHEDULE_SECONDS)
        )

    def _reset_quota_backoff(self) -> None:
        """Called after a successful LLM call to shrink the backoff."""
        self._quota_level = 0
        self._quota_until = 0.0

    @staticmethod
    def _refresh_settings() -> None:
        """Best-effort reload of Dashboard-driven settings (model, KB toggles)."""
        try:
            from pr_agent.secret_providers.postgres_provider import (
                ensure_postgres_config_loaded,
            )

            ensure_postgres_config_loaded()
        except Exception:
            # Config file + env vars still apply; not worth crashing the worker.
            pass


# =============================================================================
# Entry point
# =============================================================================


def _install_signal_handlers(worker: RefinementWorker) -> None:
    """Wire SIGTERM/SIGINT to graceful shutdown so container stops are clean."""
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except (NotImplementedError, RuntimeError):
            # Windows / non-main-thread: fall back to default Python handler.
            pass


def main() -> None:  # pragma: no cover - process entrypoint
    """Entrypoint for ``python -m pr_agent.workers.refinement``."""
    from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
    from pr_agent.log import get_logger, setup_logger
    from pr_agent.memory_providers import get_memory_provider
    from pr_agent.secret_providers.postgres_provider import (
        apply_postgres_credentials_to_config,
    )

    setup_logger()

    # Pull DB-backed config (git providers, LLM credentials, KB settings)
    # into Dynaconf before we touch the LLM or memory provider.
    try:
        apply_postgres_credentials_to_config()
    except Exception as exc:
        get_logger().warning(f"refinement.bootstrap_db_config_failed: {exc}")

    memory = get_memory_provider()
    ai = LiteLLMAIHandler()

    worker = RefinementWorker(memory_provider=memory, ai_handler=ai)
    _install_signal_handlers(worker)

    asyncio.run(worker.run_forever())


if __name__ == "__main__":  # pragma: no cover
    main()
