"""
Database connection and session management.

Uses SQLModel with PostgreSQL via psycopg2. Schema changes are applied via
Alembic (see `pr_agent.db.migrations_runner`); `create_db_and_tables` below
is retained for callers that need a low-level create_all but should not be
used as the primary bootstrap path.
"""

import os
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

# Get database URL from environment variable
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/pr_agent"
)

# Create engine
# echo=True for debugging SQL queries (disable in production)
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables() -> None:
    """Create all database tables via SQLModel metadata.

    .. deprecated::
        Prefer `pr_agent.db.migrations_runner.run_migrations(engine, DATABASE_URL)`
        for service bootstrap — it handles greenfield, legacy, and upgrade
        states in a single call and picks up future schema changes.

    This helper remains for tests and scripts that need raw table creation.
    """
    SQLModel.metadata.create_all(engine)


def init_database(logger=None) -> None:
    """Bring the connected database up to the latest schema revision.

    Thin wrapper around `migrations_runner.run_migrations` that resolves the
    engine and URL from this module so callers only need one import.
    """
    # Deferred import to avoid importing Alembic in contexts that only need
    # a session (tests, CLI tools, etc.).
    from pr_agent.db.migrations_runner import run_migrations

    run_migrations(engine, DATABASE_URL, logger=logger)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.

    Usage:
        @router.get("/providers")
        def get_providers(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session
