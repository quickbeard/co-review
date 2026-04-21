"""Add disable_auto_feedback column to pr_agent_configs.

Revision ID: 0002_add_disable_auto_feedback
Revises: 0001_baseline
Create Date: 2026-04-21

Motivation
----------
The automation dashboard (P0) originally stored the global
`disable_auto_feedback` toggle inside every provider's JSON column because no
migration tooling was available. This revision promotes it to a proper first-
class boolean column on `pr_agent_configs`, and back-fills the new column
from any surviving JSON flags before scrubbing them.

Idempotency
-----------
The upgrade is safe on legacy databases (where the column is missing AND the
JSON columns may carry the flag) and on brand-new databases (where neither
the column nor the JSON flag exists). Alembic guarantees the migration only
runs when the DB is at the prior revision, so the data-migration SQL will
not be re-run on subsequent boots.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_add_disable_auto_feedback"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Provider JSON columns that may carry the legacy `disable_auto_feedback`
# flag from the automation P0 workaround. Kept in sync with
# `pr_agent.db.models.PRAgentConfig`.
_PROVIDER_JSON_COLUMNS: tuple[str, ...] = (
    "github_app_config",
    "gitlab_config",
    "bitbucket_app_config",
    "azure_devops_config",
    "gitea_config",
)


def upgrade() -> None:
    # 1. Add the column with a server-side default so the NOT NULL constraint
    #    can be applied to existing rows atomically.
    op.add_column(
        "pr_agent_configs",
        sa.Column(
            "disable_auto_feedback",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    conn = op.get_bind()

    # The SQLModel columns use SQLAlchemy's generic JSON type, which maps to
    # Postgres `json`, not `jsonb`. Cast to `jsonb` explicitly because the
    # `?` (key exists) and `-` (remove key) operators only exist on jsonb.

    # 2. Promote any legacy JSON-embedded flag into the new column. A row is
    #    considered "disabled" if any provider config has the flag set.
    disabled_clause = " OR ".join(
        f"(({col}::jsonb ->> 'disable_auto_feedback')::boolean IS TRUE)"
        for col in _PROVIDER_JSON_COLUMNS
    )
    conn.execute(
        sa.text(
            f"UPDATE pr_agent_configs SET disable_auto_feedback = TRUE "
            f"WHERE {disabled_clause}"
        )
    )

    # 3. Strip the stale key out of every provider JSON column so the shape
    #    of stored data matches what the API now produces.
    for col in _PROVIDER_JSON_COLUMNS:
        conn.execute(
            sa.text(
                f"UPDATE pr_agent_configs SET {col} = ({col}::jsonb - 'disable_auto_feedback')::json "
                f"WHERE {col}::jsonb ? 'disable_auto_feedback'"
            )
        )

    # 4. Drop the server_default now that all rows have a value; the Python-
    #    side SQLModel default (False) continues to populate fresh inserts.
    op.alter_column("pr_agent_configs", "disable_auto_feedback", server_default=None)


def downgrade() -> None:
    # Restore the legacy JSON shape (best-effort): re-insert the flag into
    # every provider column before dropping the new one, so a rollback does
    # not silently lose state.
    conn = op.get_bind()
    for col in _PROVIDER_JSON_COLUMNS:
        conn.execute(
            sa.text(
                f"UPDATE pr_agent_configs SET {col} = "
                f"(COALESCE({col}::jsonb, '{{}}'::jsonb) || "
                f"jsonb_build_object('disable_auto_feedback', TRUE))::json "
                f"WHERE disable_auto_feedback IS TRUE"
            )
        )
    op.drop_column("pr_agent_configs", "disable_auto_feedback")
