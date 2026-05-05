"""Unit tests for pr_agent.workers.refinement.

We deliberately do NOT touch real LLM or mem0 state here. Instead we drive
:class:`RefinementWorker` with lightweight fakes so these can run in CI
without any external dependency and stay fast.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from pr_agent.workers.refinement import (
    REFINEMENT_SYSTEM_PROMPT,
    RefinementWorker,
    build_user_prompt,
    is_quota_error,
    parse_llm_output,
)


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeRecord:
    """Minimal duck-typed stand-in for :class:`LearningRecord`."""

    id: str
    text: str = "some raw feedback"
    repo: str = "acme/widgets"
    metadata: dict[str, Any] = field(default_factory=dict)


class FakeMemory:
    """In-memory mem0 double. Tracks update calls for assertions."""

    def __init__(self, pending: list[FakeRecord], *, enabled: bool = True):
        self._pending = pending
        self._enabled = enabled
        self.updates: list[dict[str, Any]] = []
        self.raise_on_update: Exception | None = None

    def is_enabled(self) -> bool:
        return self._enabled

    def list_pending_refinements(
        self, limit: int = 50, max_attempts: int | None = None
    ) -> list[FakeRecord]:
        # Mirror the real provider's contract so the worker exercises the
        # same filtering path (cap by attempts, then by limit).
        eligible = [
            r
            for r in self._pending
            if max_attempts is None
            or int(r.metadata.get("refine_attempts", 0) or 0) < max_attempts
        ]
        return eligible[:limit]

    def update_learning_after_refinement(
        self,
        learning_id: str,
        *,
        refined_text: str | None,
        status: str,
        error: str | None = None,
    ) -> bool:
        if self.raise_on_update is not None:
            raise self.raise_on_update
        self.updates.append(
            {
                "id": learning_id,
                "refined_text": refined_text,
                "status": status,
                "error": error,
            }
        )
        return True


class ScriptedAI:
    """Returns a queued response (or raises a queued exception) per call."""

    def __init__(self, script: list[Any]):
        # Each entry is either a str (LLM output) or an Exception subclass
        # instance to raise from chat_completion.
        self._script = list(script)
        self.calls: list[dict[str, Any]] = []

    async def chat_completion(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        img_path: str | None = None,
    ):
        self.calls.append(
            {"model": model, "system": system, "user": user, "temperature": temperature}
        )
        if not self._script:
            raise AssertionError("ScriptedAI ran out of scripted responses")
        next_item = self._script.pop(0)
        if isinstance(next_item, BaseException):
            raise next_item
        return next_item, "stop"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestBuildUserPrompt:
    def test_uses_raw_comment_metadata_over_record_text(self):
        record = FakeRecord(
            id="m1",
            text="short summary",
            metadata={
                "raw_comment": "Prefer early returns over nested ifs.",
                "sender_login": "alice",
                "pr_number": 42,
            },
            repo="acme/widgets",
        )

        prompt = build_user_prompt(record)

        assert "Prefer early returns over nested ifs." in prompt
        assert "short summary" not in prompt
        assert "alice" in prompt
        assert "acme/widgets" in prompt
        assert "PR #42" in prompt

    def test_falls_back_to_record_text_and_repo(self):
        record = FakeRecord(
            id="m2",
            text="Always use bcrypt for password hashing",
            repo="org/repo",
            metadata={},
        )

        prompt = build_user_prompt(record)

        assert "Always use bcrypt for password hashing" in prompt
        assert "org/repo" in prompt
        assert "unknown reviewer" in prompt
        assert "PR #" not in prompt

    def test_empty_input_still_produces_prompt(self):
        record = FakeRecord(id="m3", text="", metadata={})

        prompt = build_user_prompt(record)

        assert "(empty comment body)" in prompt


class TestParseLlmOutput:
    def test_refined_payload(self):
        out = parse_llm_output('{"refined": "Use snake_case for functions."}')

        assert out.refined_text == "Use snake_case for functions."
        assert out.rejection_reason is None
        assert not out.transient

    def test_reject_payload(self):
        out = parse_llm_output('{"reject": true, "reason": "chit-chat"}')

        assert out.rejection_reason == "chit-chat"
        assert out.refined_text is None

    def test_reject_without_reason_still_terminal(self):
        out = parse_llm_output('{"reject": true}')

        assert out.rejection_reason == "rejected without reason"

    def test_salvages_json_wrapped_in_prose(self):
        raw = 'Here you go:\n{"refined": "Prefer composition over inheritance."}\nThanks!'

        out = parse_llm_output(raw)

        assert out.refined_text == "Prefer composition over inheritance."

    def test_empty_response_is_transient(self):
        out = parse_llm_output("")

        assert out.transient is True
        assert out.refined_text is None
        assert out.rejection_reason is None

    def test_unparseable_is_transient(self):
        out = parse_llm_output("totally not json")

        assert out.transient is True

    def test_whitespace_only_refined_is_transient(self):
        out = parse_llm_output('{"refined": "   "}')

        assert out.transient is True


class TestIsQuotaError:
    def test_by_class_name(self):
        class RateLimitError(Exception):
            pass

        assert is_quota_error(RateLimitError("slow down")) is True

    def test_by_message(self):
        assert is_quota_error(RuntimeError("OpenAI: you hit the rate limit")) is True
        assert is_quota_error(RuntimeError("insufficient_quota: top up")) is True

    def test_by_status_code_attribute(self):
        exc = RuntimeError("server said no")
        exc.status_code = 429  # type: ignore[attr-defined]

        assert is_quota_error(exc) is True

    def test_unrelated_error_is_not_quota(self):
        assert is_quota_error(ValueError("bad input")) is False
        assert is_quota_error(ConnectionError("DNS oops")) is False


# ---------------------------------------------------------------------------
# run_once simulation
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async test body without depending on pytest-asyncio."""
    return asyncio.new_event_loop().run_until_complete(coro)


class TestRunOnce:
    def test_refined_record_gets_terminal_update(self):
        record = FakeRecord(
            id="m1",
            metadata={"raw_comment": "Prefer logging over print() in services."},
        )
        mem = FakeMemory([record])
        ai = ScriptedAI(['{"refined": "Use structured logging, not print()."}'])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        report = _run(worker.run_once())

        assert report.processed == 1
        assert report.refined == 1
        assert report.rejected == 0
        assert report.transient_failures == 0
        assert mem.updates == [
            {
                "id": "m1",
                "refined_text": "Use structured logging, not print().",
                "status": "refined",
                "error": None,
            }
        ]
        # The system prompt was actually passed through; catches accidental
        # refactors that drop the contract.
        assert ai.calls[0]["system"] == REFINEMENT_SYSTEM_PROMPT

    def test_rejected_record_records_reason(self):
        record = FakeRecord(id="m2", metadata={"raw_comment": "lol ok"})
        mem = FakeMemory([record])
        ai = ScriptedAI(['{"reject": true, "reason": "not technical"}'])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        report = _run(worker.run_once())

        assert report.rejected == 1
        assert mem.updates[0]["status"] == "rejected"
        assert mem.updates[0]["error"] == "not technical"
        assert mem.updates[0]["refined_text"] is None

    def test_transient_failure_keeps_status_raw_and_bumps_attempts(self):
        record = FakeRecord(id="m3", metadata={"raw_comment": "something"})
        mem = FakeMemory([record])
        # Unparseable body -> parser returns a transient outcome.
        ai = ScriptedAI(["the model forgot to return json"])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        report = _run(worker.run_once())

        assert report.refined == 0
        assert report.rejected == 0
        assert report.transient_failures == 1
        assert mem.updates[0]["status"] == "raw"
        assert mem.updates[0]["refined_text"] is None
        assert mem.updates[0]["error"]

    def test_quota_error_halts_batch_and_records_transient(self):
        class RateLimitError(Exception):
            pass

        records = [
            FakeRecord(id="m4", metadata={"raw_comment": "first"}),
            FakeRecord(id="m5", metadata={"raw_comment": "second"}),
        ]
        mem = FakeMemory(records)
        ai = ScriptedAI([RateLimitError("429 too many requests")])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        report = _run(worker.run_once())

        # Only the first record triggers a call; the batch stops after quota hit.
        assert len(ai.calls) == 1
        assert report.quota_hit is True
        assert report.processed == 1
        assert report.transient_failures == 1
        assert len(mem.updates) == 1
        assert mem.updates[0]["status"] == "raw"
        # Worker arms the backoff window.
        assert worker._quota_until > 0

    def test_successful_refinement_clears_quota_backoff(self):
        record = FakeRecord(id="m6", metadata={"raw_comment": "hello world"})
        mem = FakeMemory([record])
        ai = ScriptedAI(['{"refined": "Greet users politely in docs."}'])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)
        # Simulate an earlier quota hit still on the clock.
        worker._quota_level = 2
        worker._quota_until = 12345.0

        _run(worker.run_once())

        assert worker._quota_level == 0
        assert worker._quota_until == 0.0

    def test_disabled_memory_provider_is_noop(self):
        record = FakeRecord(id="m7")
        mem = FakeMemory([record], enabled=False)
        ai = ScriptedAI([])  # would raise AssertionError if called
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        report = _run(worker.run_once())

        assert report.processed == 0
        assert mem.updates == []
        assert ai.calls == []

    def test_record_without_id_is_skipped(self):
        record = FakeRecord(id="", metadata={"raw_comment": "x"})
        mem = FakeMemory([record])
        ai = ScriptedAI([])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        report = _run(worker.run_once())

        assert report.processed == 1
        assert report.transient_failures == 1
        # No LLM calls and no updates because we bail before dispatching.
        assert ai.calls == []
        assert mem.updates == []

    def test_update_exception_is_swallowed(self):
        record = FakeRecord(id="m8", metadata={"raw_comment": "use tuples"})
        mem = FakeMemory([record])
        mem.raise_on_update = RuntimeError("db unavailable")
        ai = ScriptedAI(['{"refined": "Prefer tuples for fixed-size records."}'])
        worker = RefinementWorker(memory_provider=mem, ai_handler=ai)

        # Must not raise out of run_once even though the update fails.
        report = _run(worker.run_once())

        assert report.processed == 1
        # Update failure means no terminal counter bump.
        assert report.refined == 0
        assert report.errors  # reason recorded
