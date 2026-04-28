"""Add devlake_sync_jobs table.

Revision ID: 0007_add_devlake_sync_jobs
Revises: 0006_add_devlake_integrations
Create Date: 2026-04-28

Motivation
----------
Persist DevLake background sync jobs so callers can poll job status and results
across process restarts and across API instances.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_add_devlake_sync_jobs"
down_revision: Union[str, None] = "0006_add_devlake_integrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devlake_sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column(
            "git_provider_id",
            sa.Integer(),
            sa.ForeignKey("git_providers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("full_sync", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("skip_collectors", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "uq_devlake_sync_jobs_job_id",
        "devlake_sync_jobs",
        ["job_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_devlake_sync_jobs_job_id",
        table_name="devlake_sync_jobs",
    )
    op.drop_table("devlake_sync_jobs")
