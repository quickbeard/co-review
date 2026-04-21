"""Programmatic Alembic invocation for PR-Agent services.

Handles three distinct install states transparently so neither local
development nor CI nor production requires a manual `alembic` CLI step:

  1. Greenfield DB (no tables): creates every current table via
     `SQLModel.metadata.create_all` and stamps the DB at `head`.
  2. Legacy DB (tables exist, no `alembic_version`): stamps at the baseline
     revision so subsequent deltas can upgrade it, then applies them.
  3. Normal DB (`alembic_version` present): runs `upgrade head`.

Call `run_migrations(engine, DATABASE_URL)` from the API service lifespan.
Webhook services remain read-only with respect to schema.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlmodel import SQLModel

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Kept in sync with `versions/0001_baseline.py`. Legacy databases (created via
# `SQLModel.metadata.create_all` before migrations existed) are stamped at
# this revision so deltas authored afterwards can still apply cleanly.
BASELINE_REVISION = "0001_baseline"

# Any table present in the original pre-migration schema works as a sentinel
# for detecting legacy databases. `git_providers` predates every refactor.
_SENTINEL_TABLE = "git_providers"


def _build_alembic_config(database_url: str) -> Config:
    """Synthesize an Alembic Config in-memory.

    Builds a Config without relying on `alembic.ini` or a specific working
    directory, so the same entry point runs in dev, CI, and Docker images
    unchanged. The migrations directory lives next to this module.
    """
    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_migrations(
    engine: Engine,
    database_url: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Bring the database up to `head`, handling all three install states.

    Safe to call on every service boot; no-ops once the schema is current.
    """
    log = logger or logging.getLogger(__name__)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    has_alembic = "alembic_version" in tables
    has_legacy_tables = _SENTINEL_TABLE in tables

    cfg = _build_alembic_config(database_url)

    if not has_alembic and not has_legacy_tables:
        # Greenfield: let SQLModel create the full current schema in one
        # shot, then mark every migration as already applied. Future boots
        # take the `has_alembic=True` branch below.
        log.info("Greenfield database detected; creating tables from SQLModel metadata")
        # Ensure every model class is imported so its table is registered
        # on SQLModel.metadata before create_all runs.
        import pr_agent.db.models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        command.stamp(cfg, "head")
        log.info("Stamped Alembic version at head")
        return

    if not has_alembic and has_legacy_tables:
        # Legacy install: tables were created by an older build that
        # pre-dates migrations. Mark it at baseline so the delta below
        # can add new columns/tables.
        log.info("Legacy database detected; stamping at %s", BASELINE_REVISION)
        command.stamp(cfg, BASELINE_REVISION)

    log.info("Applying Alembic migrations up to head")
    command.upgrade(cfg, "head")
    log.info("Alembic migrations complete")
