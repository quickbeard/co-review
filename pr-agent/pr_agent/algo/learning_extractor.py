from __future__ import annotations

import re


def extract_learning_candidate(comment_body: str, app_name: str) -> str | None:
    if not comment_body or not isinstance(comment_body, str):
        return None

    text = comment_body.strip()
    if not text or text.startswith("/"):
        return None

    # Remove direct mention to the bot/app and common addressing punctuations.
    mention_pattern = rf"@{re.escape(app_name)}\b[:,]?\s*"
    text = re.sub(mention_pattern, "", text, flags=re.IGNORECASE).strip()

    if len(text) < 20:
        return None

    lower_text = text.lower()
    preference_markers = (
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
    if not any(marker in lower_text for marker in preference_markers):
        return None

    return text
