"""Add knowledge_base_config JSON column to pr_agent_configs.

Revision ID: 0004_add_knowledge_base_config
Revises: 0003_add_webhook_registrations
Create Date: 2026-04-21

Motivation
----------
Stage 2 moves the knowledge-base controls (`/learn` toggle, extraction rules,
retrieval tuning, legacy passive flags) into the Dashboard. Rather than
add a dozen scalar columns, we store the whole section in a single JSON
blob - consistent with the other tool-scoped section columns on
``pr_agent_configs`` (`pr_reviewer_config`, `github_app_config`, ...).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_add_knowledge_base_config"
down_revision: Union[str, None] = "0003_add_webhook_registrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the ``knowledge_base_config`` JSON column."""
    op.add_column(
        "pr_agent_configs",
        sa.Column("knowledge_base_config", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``knowledge_base_config`` column."""
    op.drop_column("pr_agent_configs", "knowledge_base_config")
