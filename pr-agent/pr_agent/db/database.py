"""
Database connection and session management.

Uses SQLModel with PostgreSQL via psycopg2.
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
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


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
