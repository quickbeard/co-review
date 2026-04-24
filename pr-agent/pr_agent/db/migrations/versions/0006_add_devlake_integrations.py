"""Add devlake_integrations table.

Revision ID: 0006_add_devlake_integrations
Revises: 0005_add_pr_review_activities
Create Date: 2026-04-24

Motivation
----------
Provide a durable mapping between internal git providers and DevLake resources
(connection, blueprint, selected scopes, and latest sync status) so the
dashboard can orchestrate DevLake ingestion without depending on DevLake UI.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_add_devlake_integrations"
down_revision: Union[str, None] = "0005_add_pr_review_activities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devlake_integrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "git_provider_id",
            sa.Integer(),
            sa.ForeignKey("git_providers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("plugin_name", sa.String(length=50), nullable=True),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("blueprint_id", sa.Integer(), nullable=True),
        sa.Column("project_name", sa.String(length=255), nullable=True),
        sa.Column("selected_scopes", sa.JSON(), nullable=True),
        sa.Column("last_pipeline_id", sa.Integer(), nullable=True),
        sa.Column("last_sync_status", sa.String(length=50), nullable=True),
        sa.Column("last_sync_error", sa.String(length=2000), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
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
        "uq_devlake_integrations_git_provider_id",
        "devlake_integrations",
        ["git_provider_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_devlake_integrations_git_provider_id",
        table_name="devlake_integrations",
    )
    op.drop_table("devlake_integrations")
