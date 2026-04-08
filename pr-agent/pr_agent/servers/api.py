"""
PR-Agent REST API for Dashboard integration.

Provides CRUD endpoints for git provider management.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from pr_agent.db import (
    GitProvider,
    GitProviderCreate,
    GitProviderPublic,
    GitProviderUpdate,
    create_db_and_tables,
    get_session,
)

# Use standard logging instead of pr_agent.log to avoid dependency issues
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_logger():
    return logger

# Type alias for session dependency
SessionDep = Annotated[Session, Depends(get_session)]


# =============================================================================
# Lifespan: Initialize database on startup
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    get_logger().info("Creating database tables...")
    create_db_and_tables()
    get_logger().info("Database tables created successfully")
    yield


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="PR-Agent API",
    description="REST API for PR-Agent Dashboard integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# =============================================================================
# Git Providers CRUD
# =============================================================================

@app.get("/api/providers", response_model=list[GitProviderPublic])
def list_providers(
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[GitProvider]:
    """List all git providers."""
    statement = select(GitProvider).offset(skip).limit(limit)
    providers = session.exec(statement).all()
    return list(providers)


@app.get("/api/providers/{provider_id}", response_model=GitProviderPublic)
def get_provider(
    provider_id: int,
    session: SessionDep,
) -> GitProvider:
    """Get a single git provider by ID."""
    provider = session.get(GitProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@app.post("/api/providers", response_model=GitProviderPublic, status_code=201)
def create_provider(
    provider_data: GitProviderCreate,
    session: SessionDep,
) -> GitProvider:
    """Create a new git provider."""
    # Validate GitHub-specific requirements
    if provider_data.type.value == "github":
        if provider_data.deployment_type is None:
            provider_data.deployment_type = "user"

        if provider_data.deployment_type.value == "user":
            if not provider_data.access_token:
                raise HTTPException(
                    status_code=400,
                    detail="access_token is required for GitHub user deployment"
                )
        elif provider_data.deployment_type.value == "app":
            if not provider_data.app_id or not provider_data.private_key:
                raise HTTPException(
                    status_code=400,
                    detail="app_id and private_key are required for GitHub app deployment"
                )
    else:
        # Non-GitHub providers require access_token
        if not provider_data.access_token:
            raise HTTPException(
                status_code=400,
                detail="access_token is required"
            )

    # Create the provider
    provider = GitProvider.model_validate(provider_data)
    session.add(provider)
    session.commit()
    session.refresh(provider)

    get_logger().info(f"Created git provider: {provider.name} (type={provider.type})")
    return provider


@app.put("/api/providers/{provider_id}", response_model=GitProviderPublic)
def update_provider(
    provider_id: int,
    provider_data: GitProviderUpdate,
    session: SessionDep,
) -> GitProvider:
    """Update an existing git provider."""
    provider = session.get(GitProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Update only provided fields
    update_data = provider_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    # Update timestamp
    provider.updated_at = datetime.now(timezone.utc)

    session.add(provider)
    session.commit()
    session.refresh(provider)

    get_logger().info(f"Updated git provider: {provider.name} (id={provider.id})")
    return provider


@app.patch("/api/providers/{provider_id}", response_model=GitProviderPublic)
def patch_provider(
    provider_id: int,
    provider_data: GitProviderUpdate,
    session: SessionDep,
) -> GitProvider:
    """Partially update a git provider (e.g., toggle status)."""
    return update_provider(provider_id, provider_data, session)


@app.delete("/api/providers/{provider_id}")
def delete_provider(
    provider_id: int,
    session: SessionDep,
) -> dict[str, str]:
    """Delete a git provider."""
    provider = session.get(GitProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider_name = provider.name
    session.delete(provider)
    session.commit()

    get_logger().info(f"Deleted git provider: {provider_name} (id={provider_id})")
    return {"status": "deleted", "id": str(provider_id)}


# =============================================================================
# Main entry point
# =============================================================================

def main():
    """Run the API server."""
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "3001"))

    get_logger().info(f"Starting PR-Agent API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
