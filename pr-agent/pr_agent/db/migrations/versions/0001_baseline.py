"""Baseline (pre-Alembic schema).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-04-21

Empty by design: this revision marks the database state PRIOR to adopting
Alembic-managed migrations. It is never executed as an upgrade in practice —
one of two things happens at runtime:

* Greenfield installs get their tables created via
  `SQLModel.metadata.create_all(engine)` and are immediately stamped at
  `head`, so this revision is recorded as applied without its `upgrade()`
  body ever running.
* Legacy installs (tables created by earlier versions of the codebase via
  `create_all`) are stamped directly at this revision by the bootstrap code
  in `pr_agent.db.migrations_runner`. Subsequent deltas then upgrade them
  from this point.

See `pr_agent/db/migrations_runner.py` for the state-detection logic.
"""

from typing import Sequence, Union


revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Intentionally empty. See module docstring."""


def downgrade() -> None:
    """Intentionally empty. See module docstring."""
