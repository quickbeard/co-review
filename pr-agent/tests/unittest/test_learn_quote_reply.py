"""Quote-reply handling for the ``/learn`` command.

Covers both touchpoints that the feature requires:

* the GitHub webhook dispatcher (``_rewrite_quote_reply_with_command``) that
  reorders a ``> quoted\\n/learn`` body so the strict "must start with /"
  gate lets the command through;
* the tool-side extractor (``PRLearn._candidate_text``) that pulls the
  quoted block out as the actual learning text and annotates the
  ``quote_reply`` source for the dashboard.

We intentionally don't exercise the full ``PRLearn.run`` pipeline here -
that hits the git provider and the memory store. The two pieces below are
the pure logic that determines whether the quote-reply shape works at all,
which is what the user asked about.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Dispatcher helper (``_rewrite_quote_reply_with_command``)
# ---------------------------------------------------------------------------

from pr_agent.servers.github_app import _rewrite_quote_reply_with_command


class TestRewriteQuoteReplyWithCommand:
    def test_quote_then_learn_gets_rewritten(self):
        body = "> These are meaningless comments\n\n/learn"
        out = _rewrite_quote_reply_with_command(body)
        assert out is not None
        assert out.startswith("/learn")
        # The original quoted block is preserved on a later line so the tool
        # side can extract it.
        assert "> These are meaningless comments" in out

    def test_quote_then_learn_with_args_keeps_args(self):
        body = "> please rename\n/learn rename dead variables"
        out = _rewrite_quote_reply_with_command(body)
        assert out is not None
        # The command line (including its args) comes first.
        first_line = out.splitlines()[0]
        assert first_line == "/learn rename dead variables"

    def test_inline_command_untouched(self):
        # Body already starts with the command - nothing to rewrite.
        assert _rewrite_quote_reply_with_command("/learn foo") is None

    def test_plain_quote_without_command_untouched(self):
        # No slash command = no rewrite.
        assert _rewrite_quote_reply_with_command("> just a quote") is None

    def test_non_learn_slash_command_not_rewritten(self):
        # Only the configured ``knowledge_base.learn_command`` gets
        # reordered; other slash commands embedded in quotes keep today's
        # strict behaviour so a quoted ``/review`` can't re-trigger a
        # review.
        body = "> please rename\n\n/review"
        assert _rewrite_quote_reply_with_command(body) is None

    def test_custom_learn_command_is_honoured(self):
        # The learn command is configurable (dashboard / Dynaconf); the
        # rewriter must follow whatever the user set.
        from pr_agent.config_loader import get_settings

        previous = get_settings().get("knowledge_base.learn_command", "/learn")
        try:
            get_settings().set("knowledge_base.learn_command", "/remember")
            body = "> this is worth saving\n\n/remember"
            out = _rewrite_quote_reply_with_command(body)
            assert out is not None
            assert out.splitlines()[0] == "/remember"
            # The default command should no longer be lifted when a custom
            # command is configured.
            body_default = "> this is worth saving\n\n/learn"
            assert _rewrite_quote_reply_with_command(body_default) is None
        finally:
            get_settings().set("knowledge_base.learn_command", previous)

    def test_misconfigured_command_without_slash_is_coerced(self):
        # Someone editing the config by hand may drop the leading ``/``.
        # We auto-prefix it rather than silently matching arbitrary words
        # inside the quote block.
        from pr_agent.config_loader import get_settings

        previous = get_settings().get("knowledge_base.learn_command", "/learn")
        try:
            get_settings().set("knowledge_base.learn_command", "remember")
            body = "> this is worth saving\n\n/remember"
            out = _rewrite_quote_reply_with_command(body)
            assert out is not None
            assert out.splitlines()[0] == "/remember"
        finally:
            get_settings().set("knowledge_base.learn_command", previous)

    def test_learn_substring_on_wrapped_line_ignored(self):
        # ``/learn`` must be on its own line - a quoted mention of
        # ``/learn`` shouldn't accidentally trigger the rewriter.
        body = "> do /learn something\nthoughts?"
        assert _rewrite_quote_reply_with_command(body) is None

    def test_non_string_inputs_return_none(self):
        assert _rewrite_quote_reply_with_command(None) is None
        assert _rewrite_quote_reply_with_command("") is None

    def test_multi_line_quote_roundtrips_content(self):
        body = (
            "> Line one of the quote\n"
            "> Line two of the quote\n"
            "\n"
            "/learn"
        )
        out = _rewrite_quote_reply_with_command(body)
        assert out is not None
        assert out.splitlines()[0] == "/learn"
        assert "> Line one of the quote" in out
        assert "> Line two of the quote" in out


# ---------------------------------------------------------------------------
# Tool-side helpers (``PRLearn._unquote_lines`` + ``PRLearn._candidate_text``)
# ---------------------------------------------------------------------------


@pytest.fixture
def pr_learn_class(monkeypatch):
    """Import ``PRLearn`` with its git-provider dependency stubbed.

    ``PRLearn.__init__`` calls ``get_git_provider_with_context`` which tries
    to hit a real provider. We patch it out so the test can construct an
    instance cheaply and only inspect the candidate-text logic.
    """

    # Lazy import inside the fixture so ``monkeypatch`` can intercept before
    # the class instance is constructed in each test.
    from pr_agent.tools import pr_learn as pr_learn_module

    monkeypatch.setattr(
        pr_learn_module,
        "get_git_provider_with_context",
        lambda *_a, **_kw: MagicMock(repo="owner/repo"),
    )
    return pr_learn_module.PRLearn


def _make_tool(pr_learn_cls, *, raw_comment_body: str, parent_comment_id=None):
    """Instantiate ``PRLearn`` with a prepared ``learn_context``."""
    from pr_agent.config_loader import get_settings

    get_settings().set(
        "learn_context",
        {
            "raw_comment_body": raw_comment_body,
            "parent_comment_id": parent_comment_id,
            "comment_id": 1,
            "pr_number": 1,
            "repo_full_name": "owner/repo",
            "sender_login": "alice",
        },
    )
    # Make the extract-only helper happy regardless of how the caller set
    # up explicit-learn mode.
    get_settings().set("knowledge_base.learn_command", "/learn")
    return pr_learn_cls(pr_url="https://example.invalid/owner/repo/pull/1")


class TestUnquoteLines:
    def test_single_quote_line_strips_prefix(self, pr_learn_class):
        out = pr_learn_class._unquote_lines("> hello world")
        assert out == "hello world"

    def test_multi_line_quote_preserves_line_breaks(self, pr_learn_class):
        out = pr_learn_class._unquote_lines("> one\n> two\n> three")
        assert out == "one\ntwo\nthree"

    def test_non_quote_lines_are_dropped(self, pr_learn_class):
        out = pr_learn_class._unquote_lines("> keep me\nnot me\n> me too")
        assert out == "keep me\nme too"

    def test_empty_quote_lines_are_dropped(self, pr_learn_class):
        out = pr_learn_class._unquote_lines("> one\n>\n> two")
        assert out == "one\ntwo"

    def test_handles_no_space_after_marker(self, pr_learn_class):
        # ``>quoted`` with no following space should still lose exactly the
        # ``>`` marker.
        out = pr_learn_class._unquote_lines(">quoted")
        assert out == "quoted"


class TestCandidateTextQuoteReply:
    def test_rewritten_dispatcher_form_extracts_quote(self, pr_learn_class):
        # This matches what the dispatcher produces after rewriting
        # ``> quoted\n/learn`` into ``/learn\n> quoted``. ``/learn`` then
        # has *only* a quoted tail, so we extract and un-quote it.
        body = "/learn\n> please rename dead variables"
        tool = _make_tool(pr_learn_class, raw_comment_body=body)
        text, source = tool._candidate_text()
        assert source == "quote_reply"
        assert text == "please rename dead variables"

    def test_original_quote_then_learn_form_extracts_quote(self, pr_learn_class):
        # Belt-and-braces: even if the dispatcher rewriter doesn't run
        # (e.g. we ever loosen the gate or swap it out), the tool still
        # recovers the quote when the user's raw body has the shape
        # ``> quoted\n/learn``.
        body = "> please rename dead variables\n\n/learn"
        tool = _make_tool(pr_learn_class, raw_comment_body=body)
        text, source = tool._candidate_text()
        assert source == "quote_reply"
        assert text == "please rename dead variables"

    def test_inline_text_wins_over_quote_block(self, pr_learn_class):
        # ``/learn <text>`` where ``<text>`` is not purely a quote stays
        # "inline" - the user wrote explicit wording; we respect it.
        body = "/learn prefer const\n> unrelated quoted context"
        tool = _make_tool(pr_learn_class, raw_comment_body=body)
        text, source = tool._candidate_text()
        assert source == "inline"
        assert text.startswith("prefer const")

    def test_bare_learn_without_quote_falls_through_to_empty(self, pr_learn_class):
        body = "/learn"
        tool = _make_tool(pr_learn_class, raw_comment_body=body)
        text, source = tool._candidate_text()
        # No inline, no quote, no parent -> empty. The run() method surfaces
        # a helpful message to the user in that case.
        assert (text, source) == ("", "empty")

    def test_multi_line_quote_joined_with_newlines(self, pr_learn_class):
        body = (
            "/learn\n"
            "> Line one of the quote\n"
            "> Line two of the quote\n"
        )
        tool = _make_tool(pr_learn_class, raw_comment_body=body)
        text, source = tool._candidate_text()
        assert source == "quote_reply"
        assert text == "Line one of the quote\nLine two of the quote"
