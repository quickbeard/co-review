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
    LLMProvider,
    LLMProviderCreate,
    LLMProviderPublic,
    LLMProviderUpdate,
    LLMProviderType,
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

@app.get("/api/git-providers", response_model=list[GitProviderPublic])
def list_providers(
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[GitProvider]:
    """List all git providers."""
    statement = select(GitProvider).offset(skip).limit(limit)
    providers = session.exec(statement).all()
    return list(providers)


@app.get("/api/git-providers/{provider_id}", response_model=GitProviderPublic)
def get_provider(
    provider_id: int,
    session: SessionDep,
) -> GitProvider:
    """Get a single git provider by ID."""
    provider = session.get(GitProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@app.post("/api/git-providers", response_model=GitProviderPublic, status_code=201)
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


@app.put("/api/git-providers/{provider_id}", response_model=GitProviderPublic)
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


@app.patch("/api/git-providers/{provider_id}", response_model=GitProviderPublic)
def patch_provider(
    provider_id: int,
    provider_data: GitProviderUpdate,
    session: SessionDep,
) -> GitProvider:
    """Partially update a git provider (e.g., toggle status)."""
    return update_provider(provider_id, provider_data, session)


@app.delete("/api/git-providers/{provider_id}")
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
# LLM Providers CRUD
# =============================================================================

def llm_provider_to_public(provider: LLMProvider) -> LLMProviderPublic:
    """Convert LLMProvider to LLMProviderPublic (excludes sensitive fields)."""
    return LLMProviderPublic(
        id=provider.id,
        type=provider.type,
        name=provider.name,
        is_active=provider.is_active,
        is_default=provider.is_default,
        api_base=provider.api_base,
        organization=provider.organization,
        api_type=provider.api_type,
        api_version=provider.api_version,
        deployment_id=provider.deployment_id,
        vertex_project=provider.vertex_project,
        vertex_location=provider.vertex_location,
        aws_region_name=provider.aws_region_name,
        model_id=provider.model_id,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@app.get("/api/llm-providers", response_model=list[LLMProviderPublic])
def list_llm_providers(
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[LLMProviderPublic]:
    """List all LLM providers."""
    statement = select(LLMProvider).offset(skip).limit(limit)
    providers = session.exec(statement).all()
    return [llm_provider_to_public(p) for p in providers]


@app.get("/api/llm-providers/types")
def list_llm_provider_types() -> list[dict[str, str]]:
    """List all supported LLM provider types."""
    return [{"value": t.value, "label": t.value.replace("_", " ").title()} for t in LLMProviderType]


@app.get("/api/llm-providers/{provider_id}", response_model=LLMProviderPublic)
def get_llm_provider(
    provider_id: int,
    session: SessionDep,
) -> LLMProviderPublic:
    """Get a single LLM provider by ID."""
    provider = session.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    return llm_provider_to_public(provider)


@app.post("/api/llm-providers", response_model=LLMProviderPublic, status_code=201)
def create_llm_provider(
    provider_data: LLMProviderCreate,
    session: SessionDep,
) -> LLMProviderPublic:
    """Create a new LLM provider."""
    # Validate required fields based on provider type
    provider_type = provider_data.type

    # Most providers require an API key
    key_required_types = [
        LLMProviderType.openai,
        LLMProviderType.anthropic,
        LLMProviderType.cohere,
        LLMProviderType.replicate,
        LLMProviderType.groq,
        LLMProviderType.xai,
        LLMProviderType.huggingface,
        LLMProviderType.deepseek,
        LLMProviderType.deepinfra,
        LLMProviderType.google_ai_studio,
        LLMProviderType.openrouter,
    ]

    if provider_type in key_required_types and not provider_data.api_key:
        raise HTTPException(
            status_code=400,
            detail=f"api_key is required for {provider_type.value}"
        )

    # VertexAI requires project and location
    if provider_type == LLMProviderType.vertexai:
        if not provider_data.vertex_project or not provider_data.vertex_location:
            raise HTTPException(
                status_code=400,
                detail="vertex_project and vertex_location are required for VertexAI"
            )

    # Azure AD requires client credentials
    if provider_type == LLMProviderType.azure_ad:
        if not all([provider_data.client_id, provider_data.client_secret, provider_data.tenant_id]):
            raise HTTPException(
                status_code=400,
                detail="client_id, client_secret, and tenant_id are required for Azure AD"
            )

    # AWS Bedrock requires AWS credentials
    if provider_type == LLMProviderType.aws_bedrock:
        if not all([provider_data.aws_access_key_id, provider_data.aws_secret_access_key, provider_data.aws_region_name]):
            raise HTTPException(
                status_code=400,
                detail="aws_access_key_id, aws_secret_access_key, and aws_region_name are required for AWS Bedrock"
            )

    # Azure OpenAI requires api_key and api_base
    if provider_type == LLMProviderType.azure_openai:
        if not provider_data.api_key or not provider_data.api_base:
            raise HTTPException(
                status_code=400,
                detail="api_key and api_base are required for Azure OpenAI"
            )

    # If setting as default, unset other defaults
    if provider_data.is_default:
        statement = select(LLMProvider).where(LLMProvider.is_default == True)
        existing_defaults = session.exec(statement).all()
        for p in existing_defaults:
            p.is_default = False
            session.add(p)

    # Create the provider
    provider = LLMProvider.model_validate(provider_data)
    session.add(provider)
    session.commit()
    session.refresh(provider)

    get_logger().info(f"Created LLM provider: {provider.name} (type={provider.type})")
    return llm_provider_to_public(provider)


@app.put("/api/llm-providers/{provider_id}", response_model=LLMProviderPublic)
def update_llm_provider(
    provider_id: int,
    provider_data: LLMProviderUpdate,
    session: SessionDep,
) -> LLMProviderPublic:
    """Update an existing LLM provider."""
    provider = session.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")

    # If setting as default, unset other defaults
    if provider_data.is_default:
        statement = select(LLMProvider).where(LLMProvider.is_default == True, LLMProvider.id != provider_id)
        existing_defaults = session.exec(statement).all()
        for p in existing_defaults:
            p.is_default = False
            session.add(p)

    # Update only provided fields
    update_data = provider_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    # Update timestamp
    provider.updated_at = datetime.now(timezone.utc)

    session.add(provider)
    session.commit()
    session.refresh(provider)

    get_logger().info(f"Updated LLM provider: {provider.name} (id={provider.id})")
    return llm_provider_to_public(provider)


@app.patch("/api/llm-providers/{provider_id}", response_model=LLMProviderPublic)
def patch_llm_provider(
    provider_id: int,
    provider_data: LLMProviderUpdate,
    session: SessionDep,
) -> LLMProviderPublic:
    """Partially update an LLM provider (e.g., toggle status)."""
    return update_llm_provider(provider_id, provider_data, session)


@app.delete("/api/llm-providers/{provider_id}")
def delete_llm_provider(
    provider_id: int,
    session: SessionDep,
) -> dict[str, str]:
    """Delete an LLM provider."""
    provider = session.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")

    provider_name = provider.name
    session.delete(provider)
    session.commit()

    get_logger().info(f"Deleted LLM provider: {provider_name} (id={provider_id})")
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
