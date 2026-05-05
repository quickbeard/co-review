"""PR review activity audit service.

Append-only log of every PR-Agent tool invocation. Drives the dashboard's
"Reviewed PRs" counter and acts as the long-term audit trail that we'll
later expose in a per-repo view.

Two public entry points:

``record_activity(...)``
    Fire-and-forget write from ``PRAgent._handle_request``. Swallows any
    exception so a DB hiccup never breaks a review.

``get_stats(...)``
    Aggregates for the dashboard API endpoint.

Keeping the service in its own module (rather than folding into
``pr_agent/db``) lets us add CLI inspection tools and future retention
policies without touching the schema layer.
"""
from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, distinct, func, select
from sqlmodel import Session

from pr_agent.db.database import engine
from pr_agent.db.models import (
    PRReviewActivity,
    PRReviewActivityStats,
    PRReviewTriggeredBy,
)
from pr_agent.log import get_logger


# Canonical tool names - the keys used by ``command2class`` in
# pr_agent.agent.pr_agent. Keeping an alias table here lets us fold
# "review_pr" into "review" for stats without losing the specific tool
# name at record time.
TOOL_ALIASES: dict[str, str] = {
    "review_pr": "review",
    "answer": "review",
    "improve_code": "improve",
    "describe_pr": "describe",
    "ask_question": "ask",
}

# Tools that count for the homepage "Reviewed PRs" card. Intentionally narrow:
# only commands that produce review-like output on the PR. ``ask`` is excluded
# because a question doesn't mean the PR was reviewed.
REVIEW_TOOLS: frozenset[str] = frozenset({
    "review",
    "auto_review",
    "improve",
    "describe",
})


_GITHUB_URL = re.compile(r"^https?://([^/]+)/([^/]+/[^/]+)/pull[s]?/(\d+)")
_GITLAB_URL = re.compile(
    r"^https?://([^/]+)/(.+?)/-/merge_requests/(\d+)"
)
_BITBUCKET_URL = re.compile(
    r"^https?://([^/]+)/([^/]+/[^/]+)/pull-requests/(\d+)"
)
_AZURE_URL = re.compile(
    r"^https?://([^/]+)/([^/]+/[^/]+)/_git/([^/]+)/pullrequest/(\d+)"
)


def _normalise_tool(tool: str) -> str:
    """Map CLI / webhook variants onto the canonical command name."""
    tool = (tool or "").strip().lstrip("/").lower()
    return TOOL_ALIASES.get(tool, tool)


def _parse_pr_url(pr_url: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Best-effort (provider_type, repo, pr_number) extraction.

    Regexes cover the common hosted providers. For self-hosted or unknown
    URLs we return ``(None, None, None)`` rather than guessing - the
    audit row is still useful without a repo identifier.
    """
    if not pr_url:
        return (None, None, None)

    try:
        decoded = urllib.parse.unquote(pr_url)
    except Exception:
        decoded = pr_url

    m = _GITHUB_URL.match(decoded)
    if m:
        return ("github", m.group(2), int(m.group(3)))

    m = _GITLAB_URL.match(decoded)
    if m:
        return ("gitlab", m.group(2), int(m.group(3)))

    m = _BITBUCKET_URL.match(decoded)
    if m:
        host = m.group(1)
        provider = "bitbucket_server" if "bitbucket.org" not in host else "bitbucket"
        return (provider, m.group(2), int(m.group(3)))

    m = _AZURE_URL.match(decoded)
    if m:
        return ("azure_devops", f"{m.group(2)}/{m.group(3)}", int(m.group(4)))

    return (None, None, None)


def record_activity(
    *,
    tool: str,
    pr_url: Optional[str],
    triggered_by: PRReviewTriggeredBy | str = PRReviewTriggeredBy.unknown,
    success: bool = True,
    duration_ms: Optional[int] = None,
    provider_type: Optional[str] = None,
    repo: Optional[str] = None,
    pr_number: Optional[int] = None,
    created_at: Optional[datetime] = None,
) -> None:
    """Record a tool invocation. Never propagates exceptions to upstream callers.

    ``repo``/``pr_number``/``provider_type`` are best-effort derived from
    the PR URL when not supplied. The call is intentionally fire-and-forget:
    if the DB is down we log at warning level and move on so a tool run
    is never aborted by an audit-log failure.
    """
    try:
        tool_name = _normalise_tool(tool)
        if not tool_name:
            return

        parsed_provider, parsed_repo, parsed_pr = _parse_pr_url(pr_url)
        resolved_provider = provider_type or parsed_provider
        resolved_repo = repo or parsed_repo
        resolved_pr = pr_number or parsed_pr

        trigger = (
            triggered_by
            if isinstance(triggered_by, PRReviewTriggeredBy)
            else PRReviewTriggeredBy(str(triggered_by))
        )

        row = PRReviewActivity(
            tool=tool_name,
            pr_url=pr_url,
            provider_type=resolved_provider,
            repo=resolved_repo,
            pr_number=resolved_pr,
            triggered_by=trigger,
            success=success,
            duration_ms=duration_ms,
            created_at=created_at or datetime.now(timezone.utc),
        )
        with Session(engine) as session:
            session.add(row)
            session.commit()
    except Exception as e:
        # Never propagate - the primary tool run has already succeeded by
        # the time this is invoked, and losing an audit row is preferable
        # to masking the real review output with a 500.
        get_logger().warning(
            f"Failed to record PR review activity ({tool} on {pr_url}): {e}"
        )


def _count_unique_prs(session: Session, where_clauses: list) -> int:
    """Count distinct ``(repo, pr_number)`` tuples matching ``where_clauses``.

    Implemented as a subquery + outer count so it's portable across the
    SQLite used by unit tests and the PostgreSQL we run in production -
    ``count(DISTINCT (a, b))`` isn't supported by SQLite.
    """
    clauses = [
        PRReviewActivity.repo.is_not(None),
        PRReviewActivity.pr_number.is_not(None),
        *where_clauses,
    ]
    subq = (
        select(PRReviewActivity.repo, PRReviewActivity.pr_number)
        .where(and_(*clauses))
        .distinct()
        .subquery()
    )
    row = session.execute(select(func.count()).select_from(subq)).one_or_none()
    return int(row[0] or 0) if row else 0


def get_stats(
    *,
    repo: Optional[str] = None,
) -> PRReviewActivityStats:
    """Aggregate counters for the dashboard card + detail view.

    All queries are repo-scoped when ``repo`` is provided so the same
    endpoint can back both a global card and per-repo widgets later.
    """
    repo_clause = [PRReviewActivity.repo == repo] if repo else []
    try:
        with Session(engine) as session:
            base_where = and_(*repo_clause) if repo_clause else None

            total_stmt = select(func.count()).select_from(PRReviewActivity)
            if base_where is not None:
                total_stmt = total_stmt.where(base_where)
            total_row = session.execute(total_stmt).one_or_none()
            total = int(total_row[0] or 0) if total_row else 0

            successful_stmt = (
                select(func.count())
                .select_from(PRReviewActivity)
                .where(PRReviewActivity.success.is_(True))
            )
            if base_where is not None:
                successful_stmt = successful_stmt.where(base_where)
            successful_row = session.execute(successful_stmt).one_or_none()
            successful = int(successful_row[0] or 0) if successful_row else 0

            unique_prs = _count_unique_prs(session, repo_clause)

            repos_stmt = select(
                func.count(distinct(PRReviewActivity.repo))
            ).where(PRReviewActivity.repo.is_not(None))
            if repo_clause:
                repos_stmt = repos_stmt.where(*repo_clause)
            unique_repos_row = session.execute(repos_stmt).one_or_none()
            unique_repos = (
                int(unique_repos_row[0] or 0) if unique_repos_row else 0
            )

            # "Reviewed PRs" card: distinct PRs where at least one of the
            # review tools ran.
            review_unique_prs = _count_unique_prs(
                session,
                repo_clause + [PRReviewActivity.tool.in_(list(REVIEW_TOOLS))],
            )

            # Per-tool + per-trigger breakdowns.
            by_tool: dict[str, int] = {}
            tool_stmt = (
                select(PRReviewActivity.tool, func.count())
                .group_by(PRReviewActivity.tool)
            )
            if repo_clause:
                tool_stmt = tool_stmt.where(*repo_clause)
            for row in session.execute(tool_stmt).all():
                by_tool[str(row[0])] = int(row[1])

            by_trigger: dict[str, int] = {}
            trigger_stmt = (
                select(PRReviewActivity.triggered_by, func.count())
                .group_by(PRReviewActivity.triggered_by)
            )
            if repo_clause:
                trigger_stmt = trigger_stmt.where(*repo_clause)
            for row in session.execute(trigger_stmt).all():
                key = row[0]
                # SQLAlchemy returns the enum instance for Enum columns; fall
                # back to the raw value when a plain string slipped through.
                if hasattr(key, "value"):
                    key = key.value
                by_trigger[str(key)] = int(row[1])

            return PRReviewActivityStats(
                total_invocations=total,
                successful_invocations=successful,
                unique_prs=unique_prs,
                unique_repos=unique_repos,
                review_tools_unique_prs=review_unique_prs,
                by_tool=by_tool,
                by_trigger=by_trigger,
            )
    except Exception as e:
        get_logger().warning(f"Failed to compute PR review activity stats: {e}")
        return PRReviewActivityStats()


def list_activities(
    *,
    repo: Optional[str] = None,
    tool: Optional[str] = None,
    limit: int = 100,
) -> list[PRReviewActivity]:
    """Return the newest ``limit`` activities matching the filters."""
    limit = max(1, min(500, int(limit or 100)))
    try:
        with Session(engine) as session:
            stmt = select(PRReviewActivity).order_by(
                PRReviewActivity.created_at.desc()
            ).limit(limit)
            if repo:
                stmt = stmt.where(PRReviewActivity.repo == repo)
            if tool:
                stmt = stmt.where(PRReviewActivity.tool == _normalise_tool(tool))
            return list(session.execute(stmt).scalars().all())
    except Exception as e:
        get_logger().warning(f"Failed to list PR review activities: {e}")
        return []
