from __future__ import annotations

import re

MIN_LEARNING_LENGTH = 20

PREFERENCE_MARKERS: tuple[str, ...] = (
    "we prefer",
    "in this project",
    "in this repo",
    "we always",
    "we never",
    "our standard",
    "our convention",
    "please avoid",
    "do not suggest",
    "should use",
    "shouldn't use",
)


def contains_preference_marker(text: str) -> bool:
    """Return True when `text` contains at least one preference-shaped phrase.

    Used as the secondary guardrail for both the passive (`@pr-agent`) capture
    path and the explicit `/learn` command path. Keeping a single predicate
    ensures both surfaces apply the same "is this actually a preference?" test
    so the knowledge base does not fill with casual chatter.
    """
    if not text:
        return False
    lower_text = text.lower()
    return any(marker in lower_text for marker in PREFERENCE_MARKERS)


def extract_learning_candidate(comment_body: str, app_name: str) -> str | None:
    """Passive extractor: strip `@<app_name>` mention and require marker phrase.

    DEPRECATED: this drives the legacy passive capture path. New installs should
    use the `/learn` command instead. Keeping the function in place lets us
    honour existing configurations until the follow-up PR removes it.
    """
    if not comment_body or not isinstance(comment_body, str):
        return None

    text = comment_body.strip()
    if not text or text.startswith("/"):
        return None

    mention_pattern = rf"@{re.escape(app_name)}\b[:,]?\s*"
    text = re.sub(mention_pattern, "", text, flags=re.IGNORECASE).strip()

    if len(text) < MIN_LEARNING_LENGTH:
        return None

    if not contains_preference_marker(text):
        return None

    return text


def extract_learning_from_rules(
    comment_body: str,
    rules: list[str] | tuple[str, ...],
) -> tuple[str, str] | None:
    """Automatic extractor used when ``explicit_learn_enabled = false``.

    Returns ``(matched_text, matched_rule)`` when any rule appears in the
    comment body as a case-insensitive substring, or ``None`` when nothing
    matches (including the common case of an empty ``rules`` list). Slash
    commands are skipped so a reviewer typing ``/review`` is never mistaken
    for a learning.

    The returned text is the full stripped comment body, not just the span
    around the match. That way the refinement worker gets enough context to
    produce a coherent normative sentence.
    """
    if not comment_body or not isinstance(comment_body, str):
        return None
    if not rules:
        return None

    text = comment_body.strip()
    if not text or text.startswith("/"):
        return None

    lowered_text = text.lower()
    for rule in rules:
        if not rule or not isinstance(rule, str):
            continue
        rule_stripped = rule.strip()
        if not rule_stripped:
            continue
        if rule_stripped.lower() in lowered_text:
            return text, rule_stripped
    return None


def extract_explicit_learning(
    comment_body: str,
    command_token: str = "/learn",
) -> str | None:
    """Explicit extractor for the `/learn <text>` command path.

    Strips the leading command token and returns whatever non-empty text
    remains. The explicit command is treated as a trusted signal: if a user
    types `/learn`, we store what they typed verbatim. A future administrator
    opt-out (via the Dashboard) may attach a ruleset that would be enforced
    here, but today there is no content gate beyond "non-empty".
    """
    if not comment_body or not isinstance(comment_body, str):
        return None

    text = comment_body.strip()
    if not text:
        return None

    lowered_cmd = command_token.lower()
    if text.lower().startswith(lowered_cmd):
        text = text[len(lowered_cmd):].lstrip(" :,-").strip()

    if not text:
        return None

    return text
