"""Add webhook_registrations table.

Revision ID: 0003_add_webhook_registrations
Revises: 0002_add_disable_auto_feedback
Create Date: 2026-04-21

Motivation
----------
P1 introduces a per-repository webhook registry. Each row stores the webhook
config we want on a specific remote repo (target URL, secret, events) plus
cached bookkeeping (external id returned by the provider, last delivery
status). The table is created fresh here; no data migration is required.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_add_webhook_registrations"
down_revision: Union[str, None] = "0002_add_disable_auto_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the webhook_registrations table."""
    op.create_table(
        "webhook_registrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "git_provider_id",
            sa.Integer(),
            sa.ForeignKey("git_providers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("repo", sa.String(length=500), nullable=False, index=True),
        sa.Column("target_url", sa.String(length=1000), nullable=False),
        # Event list as JSON. Nullable so callers can pass NULL to mean "provider default".
        sa.Column("events", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("content_type", sa.String(length=20), nullable=False, server_default="json"),
        sa.Column("insecure_ssl", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("secret", sa.String(length=500), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True, index=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
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

    # Unique constraint to avoid double-registering the same (provider, repo, url).
    op.create_index(
        "uq_webhook_registrations_provider_repo_url",
        "webhook_registrations",
        ["git_provider_id", "repo", "target_url"],
        unique=True,
    )


def downgrade() -> None:
    """Drop the webhook_registrations table."""
    op.drop_index(
        "uq_webhook_registrations_provider_repo_url",
        table_name="webhook_registrations",
    )
    op.drop_table("webhook_registrations")
