"""Add pr_review_activities table.

Revision ID: 0005_add_pr_review_activities
Revises: 0004_add_knowledge_base_config
Create Date: 2026-04-21

Motivation
----------
The dashboard homepage needs a "Reviewed PRs" counter and per-tool activity
history. Rather than synthesising this from Mem0 (which only knows about
captured learnings) or reprocessing provider webhook deliveries, we write a
cheap append-only row every time `PRAgent._handle_request` finishes a tool
invocation. The table is indexed on the access patterns we care about:
`(repo, pr_number)` for unique-PR counting and `created_at` for recent
activity views.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_add_pr_review_activities"
down_revision: Union[str, None] = "0004_add_knowledge_base_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pr_review_activities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider_type", sa.String(length=50), nullable=True),
        sa.Column("repo", sa.String(length=500), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("pr_url", sa.String(length=1000), nullable=True),
        sa.Column("tool", sa.String(length=64), nullable=False),
        sa.Column(
            "triggered_by",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_pr_review_activities_repo", "pr_review_activities", ["repo"]
    )
    op.create_index(
        "ix_pr_review_activities_pr_number",
        "pr_review_activities",
        ["pr_number"],
    )
    op.create_index(
        "ix_pr_review_activities_tool", "pr_review_activities", ["tool"]
    )
    op.create_index(
        "ix_pr_review_activities_provider_type",
        "pr_review_activities",
        ["provider_type"],
    )
    op.create_index(
        "ix_pr_review_activities_created_at",
        "pr_review_activities",
        ["created_at"],
    )
    # Composite index tuned for "unique PR" queries: we group by (repo,
    # pr_number) for the homepage card, and the planner can walk this index
    # to answer that without touching the table.
    op.create_index(
        "ix_pr_review_activities_repo_pr",
        "pr_review_activities",
        ["repo", "pr_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pr_review_activities_repo_pr", table_name="pr_review_activities"
    )
    op.drop_index(
        "ix_pr_review_activities_created_at",
        table_name="pr_review_activities",
    )
    op.drop_index(
        "ix_pr_review_activities_provider_type",
        table_name="pr_review_activities",
    )
    op.drop_index(
        "ix_pr_review_activities_tool", table_name="pr_review_activities"
    )
    op.drop_index(
        "ix_pr_review_activities_pr_number",
        table_name="pr_review_activities",
    )
    op.drop_index(
        "ix_pr_review_activities_repo", table_name="pr_review_activities"
    )
    op.drop_table("pr_review_activities")
