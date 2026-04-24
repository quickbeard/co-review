"""Unit tests for pr_agent.services.pr_review_activity.

We swap the service's module-level ``engine`` for an in-memory SQLite
engine so this suite stays hermetic and fast. ``PRReviewActivity`` uses
only JSON-portable column types (plus a string-backed Enum), so SQLite is
a faithful stand-in for PostgreSQL here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import SQLModel, create_engine

from pr_agent.db.models import PRReviewActivity, PRReviewTriggeredBy
from pr_agent.services import pr_review_activity as svc


@pytest.fixture()
def sqlite_engine(monkeypatch):
    """Fresh in-memory SQLite engine wired into the service module."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[PRReviewActivity.__table__])
    monkeypatch.setattr(svc, "engine", engine)
    return engine


class TestParsePrUrl:
    def test_github_pr(self):
        provider, repo, num = svc._parse_pr_url(
            "https://github.com/acme/widgets/pull/42"
        )
        assert (provider, repo, num) == ("github", "acme/widgets", 42)

    def test_gitlab_mr(self):
        provider, repo, num = svc._parse_pr_url(
            "https://gitlab.com/group/sub/widgets/-/merge_requests/9"
        )
        assert provider == "gitlab"
        assert repo == "group/sub/widgets"
        assert num == 9

    def test_bitbucket_cloud(self):
        provider, repo, num = svc._parse_pr_url(
            "https://bitbucket.org/acme/widgets/pull-requests/3"
        )
        assert (provider, repo, num) == ("bitbucket", "acme/widgets", 3)

    def test_unknown_returns_nones(self):
        assert svc._parse_pr_url("not-a-url") == (None, None, None)
        assert svc._parse_pr_url(None) == (None, None, None)


class TestNormaliseTool:
    def test_aliases(self):
        assert svc._normalise_tool("/review_pr") == "review"
        assert svc._normalise_tool("describe_pr") == "describe"
        assert svc._normalise_tool("IMPROVE_CODE") == "improve"
        assert svc._normalise_tool("review") == "review"

    def test_empty(self):
        assert svc._normalise_tool("") == ""
        assert svc._normalise_tool(None) == ""  # type: ignore[arg-type]


class TestRecordAndStats:
    def test_records_activity_with_derived_fields(self, sqlite_engine):
        svc.record_activity(
            tool="/review",
            pr_url="https://github.com/acme/widgets/pull/42",
        )

        rows = svc.list_activities()
        assert len(rows) == 1
        row = rows[0]
        assert row.tool == "review"
        assert row.repo == "acme/widgets"
        assert row.pr_number == 42
        assert row.provider_type == "github"
        assert row.triggered_by == PRReviewTriggeredBy.unknown
        assert row.success is True

    def test_record_never_raises_on_bad_input(self, sqlite_engine):
        # Unknown ``triggered_by`` would ordinarily raise from the Enum ctor;
        # the service must swallow it and log instead so a real review is
        # never aborted by an audit-log bug.
        svc.record_activity(
            tool="review",
            pr_url="https://github.com/acme/widgets/pull/1",
            triggered_by="not-a-valid-trigger",  # type: ignore[arg-type]
        )
        # Nothing inserted, and no exception propagated.
        assert svc.list_activities() == []

    def test_stats_unique_prs_and_review_tools(self, sqlite_engine):
        base_url = "https://github.com/acme/widgets"
        svc.record_activity(tool="review", pr_url=f"{base_url}/pull/1")
        svc.record_activity(tool="review", pr_url=f"{base_url}/pull/1")  # dup
        svc.record_activity(tool="improve", pr_url=f"{base_url}/pull/2")
        svc.record_activity(tool="ask", pr_url=f"{base_url}/pull/3")
        svc.record_activity(
            tool="describe", pr_url="https://github.com/acme/other/pull/1"
        )

        stats = svc.get_stats()
        assert stats.total_invocations == 5
        assert stats.successful_invocations == 5
        # PR#1, PR#2, PR#3 in widgets + PR#1 in other = 4 unique PRs
        assert stats.unique_prs == 4
        # Two distinct repos
        assert stats.unique_repos == 2
        # "Reviewed" PRs excludes /ask -> PR#1, PR#2 in widgets + PR#1 in other
        assert stats.review_tools_unique_prs == 3
        assert stats.by_tool == {
            "review": 2,
            "improve": 1,
            "ask": 1,
            "describe": 1,
        }

    def test_stats_scoped_by_repo(self, sqlite_engine):
        svc.record_activity(
            tool="review", pr_url="https://github.com/a/b/pull/1"
        )
        svc.record_activity(
            tool="review", pr_url="https://github.com/c/d/pull/1"
        )

        stats = svc.get_stats(repo="a/b")
        assert stats.total_invocations == 1
        assert stats.unique_prs == 1
        assert stats.unique_repos == 1

    def test_stats_handles_null_repo_gracefully(self, sqlite_engine):
        svc.record_activity(tool="review", pr_url="garbage")
        svc.record_activity(tool="review", pr_url=None)

        stats = svc.get_stats()
        # Rows still recorded (audit trail), but neither contributes to the
        # "unique PR" counters since we can't identify the PR.
        assert stats.total_invocations == 2
        assert stats.unique_prs == 0
        assert stats.unique_repos == 0
        assert stats.review_tools_unique_prs == 0

    def test_failed_invocations_are_counted_but_not_successful(
        self, sqlite_engine
    ):
        svc.record_activity(
            tool="review",
            pr_url="https://github.com/a/b/pull/1",
            success=False,
        )
        svc.record_activity(
            tool="review",
            pr_url="https://github.com/a/b/pull/1",
            success=True,
        )

        stats = svc.get_stats()
        assert stats.total_invocations == 2
        assert stats.successful_invocations == 1
        assert stats.unique_prs == 1

    def test_list_activities_respects_tool_filter_and_order(
        self, sqlite_engine
    ):
        now = datetime.now(timezone.utc)
        svc.record_activity(
            tool="review",
            pr_url="https://github.com/a/b/pull/1",
            created_at=now - timedelta(minutes=5),
        )
        svc.record_activity(
            tool="improve",
            pr_url="https://github.com/a/b/pull/1",
            created_at=now,
        )

        # Newest first
        rows = svc.list_activities()
        assert [r.tool for r in rows] == ["improve", "review"]

        filtered = svc.list_activities(tool="review")
        assert [r.tool for r in filtered] == ["review"]

    def test_by_trigger_normalises_enum_values(self, sqlite_engine):
        svc.record_activity(
            tool="review",
            pr_url="https://github.com/a/b/pull/1",
            triggered_by=PRReviewTriggeredBy.manual,
        )
        svc.record_activity(
            tool="auto_review",
            pr_url="https://github.com/a/b/pull/2",
            triggered_by=PRReviewTriggeredBy.automatic,
        )

        stats = svc.get_stats()
        assert stats.by_trigger.get("manual") == 1
        assert stats.by_trigger.get("automatic") == 1
