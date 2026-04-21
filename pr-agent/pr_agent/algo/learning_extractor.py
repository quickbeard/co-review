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


def extract_explicit_learning(
    comment_body: str,
    command_token: str = "/learn",
) -> str | None:
    """Explicit extractor for the `/learn <text>` command path.

    Strips the leading command token and returns the remaining text only if it
    still looks like a preference (reuses `PREFERENCE_MARKERS`). Returns `None`
    when the comment is too short or does not match any marker, so the caller
    can respond with a helpful rejection message.

    The marker gate is intentional: until we ship per-user permissions, the
    flag + marker combination is the only line of defence against someone
    typing `/learn lol` and polluting the knowledge base.
    """
    if not comment_body or not isinstance(comment_body, str):
        return None

    text = comment_body.strip()
    if not text:
        return None

    lowered_cmd = command_token.lower()
    if text.lower().startswith(lowered_cmd):
        text = text[len(lowered_cmd):].lstrip(" :,-").strip()

    if len(text) < MIN_LEARNING_LENGTH:
        return None

    if not contains_preference_marker(text):
        return None

    return text
