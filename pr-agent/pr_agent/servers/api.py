"""
PR-Agent REST API for Dashboard integration.

Provides CRUD endpoints for git provider management.
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Annotated, Any

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from pr_agent.db import (
    DevLakeIntegration,
    DevLakeIntegrationPublic,
    DevLakeIntegrationUpdate,
    GitProvider,
    GitProviderCreate,
    GitProviderPublic,
    GitProviderType,
    GitProviderUpdate,
    LLMProvider,
    LLMProviderCreate,
    LLMProviderPublic,
    LLMProviderUpdate,
    LLMProviderType,
    PRAgentConfig,
    PRReviewActivityPublic,
    PRReviewActivityStats,
    WebhookDelivery,
    WebhookRegistration,
    WebhookRegistrationCreate,
    WebhookRegistrationPublic,
    WebhookRegistrationStatus,
    WebhookRegistrationUpdate,
    engine,
    get_session,
    init_database,
)
from pr_agent.services import pr_review_activity as review_activity_service
from pr_agent.services import devlake as devlake_service
from pr_agent.memory_providers import get_memory_provider
from pr_agent.memory_providers.base import LearningRecord

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
    """Bring the database schema up to date on startup.

    Delegates to `init_database`, which runs Alembic migrations against the
    configured `DATABASE_URL`. Safe to call on every boot — it is a no-op
    when the schema is already current.
    """
    get_logger().info("Running database migrations...")
    init_database(logger=get_logger())
    get_logger().info("Database migrations complete")
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
    auto_sync_on_create: bool = Query(
        default=False,
        description="If true, attempt DevLake sync right after provider creation",
    ),
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

    if auto_sync_on_create:
        integration = _get_or_create_integration(session, provider.id)  # type: ignore[arg-type]
        try:
            _sync_provider_to_devlake(
                session=session,
                provider=provider,
                integration=integration,
                full_sync=False,
                skip_collectors=False,
            )
        except HTTPException as exc:
            # Keep provider creation successful; persist failure details so callers
            # can inspect and retry via /devlake/sync.
            integration.last_sync_status = "failed"
            integration.last_sync_error = str(exc.detail)
            integration.last_synced_at = datetime.now(timezone.utc)
            integration.updated_at = datetime.now(timezone.utc)
            session.add(integration)
            session.commit()
            get_logger().warning(
                "Auto DevLake sync failed for provider id=%s: %s",
                provider.id,
                exc.detail,
            )

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
# DevLake integration (backend-only, UI wiring follows in a separate PR)
# =============================================================================


class DevLakeRemoteScopesResponse(BaseModel):
    scopes: list[dict]
    count: int


class DevLakeSyncRequest(BaseModel):
    full_sync: bool = False
    skip_collectors: bool = False


class DevLakeSyncAcceptedResponse(BaseModel):
    job_id: str
    status: str


class DevLakeSyncResponse(BaseModel):
    status: str
    plugin_name: str
    connection_id: int
    blueprint_id: int
    pipeline_id: int | None = None


class DevLakeSyncJobStatusResponse(BaseModel):
    job_id: str
    status: str
    provider_id: int
    started_at: str
    finished_at: str | None = None
    result: DevLakeSyncResponse | None = None
    error: str | None = None


class DevLakeValidationResponse(BaseModel):
    success: bool
    plugin_name: str
    connection_id: int
    remote_scope_count: int
    message: str


_devlake_sync_jobs: dict[str, dict[str, Any]] = {}
_devlake_sync_jobs_lock = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_sync_job_state(job_id: str, **updates: Any) -> None:
    with _devlake_sync_jobs_lock:
        existing = _devlake_sync_jobs.get(job_id, {})
        existing.update(updates)
        _devlake_sync_jobs[job_id] = existing


def _get_devlake_provider_or_404(session: Session, provider_id: int) -> GitProvider:
    provider = session.get(GitProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


def _integration_to_public(row: DevLakeIntegration) -> DevLakeIntegrationPublic:
    return DevLakeIntegrationPublic(
        id=row.id,  # type: ignore[arg-type]
        git_provider_id=row.git_provider_id,
        enabled=row.enabled,
        plugin_name=row.plugin_name,
        connection_id=row.connection_id,
        blueprint_id=row.blueprint_id,
        project_name=row.project_name,
        selected_scopes=list(row.selected_scopes or []),
        last_pipeline_id=row.last_pipeline_id,
        last_sync_status=row.last_sync_status,
        last_sync_error=row.last_sync_error,
        last_synced_at=row.last_synced_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_or_create_integration(session: Session, provider_id: int) -> DevLakeIntegration:
    statement = select(DevLakeIntegration).where(DevLakeIntegration.git_provider_id == provider_id)
    row = session.exec(statement).first()
    if row:
        return row
    row = DevLakeIntegration(git_provider_id=provider_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _ensure_devlake_connection(
    *,
    provider: GitProvider,
    integration: DevLakeIntegration,
) -> tuple[str, devlake_service.DevLakeClient]:
    plugin_name = devlake_service.map_provider_to_plugin(provider)
    client = devlake_service.DevLakeClient(devlake_service.load_settings())
    if integration.connection_id:
        return plugin_name, client

    conn_payload = devlake_service.build_connection_payload(provider, plugin_name)
    conn = client.create_connection(plugin_name, conn_payload)
    conn_id = conn.get("id")
    if not isinstance(conn_id, int):
        raise HTTPException(status_code=502, detail=f"Unexpected DevLake connection payload: {conn}")
    integration.connection_id = conn_id
    integration.plugin_name = plugin_name
    return plugin_name, client


def _sync_provider_to_devlake(
    *,
    session: Session,
    provider: GitProvider,
    integration: DevLakeIntegration,
    full_sync: bool,
    skip_collectors: bool,
) -> DevLakeSyncResponse:
    plugin_name, client = _ensure_devlake_connection(
        provider=provider,
        integration=integration,
    )

    selected_scopes = list(integration.selected_scopes or [])
    if selected_scopes:
        client.put_scopes(plugin_name, integration.connection_id, selected_scopes)  # type: ignore[arg-type]

    if not integration.project_name:
        integration.project_name = f"{provider.type.value}-{provider.id}"

    blueprint_payload = devlake_service.build_blueprint_payload(
        integration=integration,
        plugin_name=plugin_name,
    )

    if integration.blueprint_id:
        bp = client.patch_blueprint(integration.blueprint_id, blueprint_payload)
    else:
        bp = client.create_blueprint(blueprint_payload)
        bp_id = bp.get("id")
        if not isinstance(bp_id, int):
            raise HTTPException(status_code=502, detail=f"Unexpected DevLake blueprint payload: {bp}")
        integration.blueprint_id = bp_id

    pipeline = client.trigger_blueprint(
        integration.blueprint_id,  # type: ignore[arg-type]
        full_sync=full_sync,
        skip_collectors=skip_collectors,
    )

    integration.plugin_name = plugin_name
    integration.last_pipeline_id = pipeline.get("id") if isinstance(pipeline.get("id"), int) else None
    integration.last_sync_status = "triggered"
    integration.last_sync_error = None
    integration.last_synced_at = datetime.now(timezone.utc)
    integration.updated_at = datetime.now(timezone.utc)
    session.add(integration)
    session.commit()
    session.refresh(integration)

    return DevLakeSyncResponse(
        status="triggered",
        plugin_name=plugin_name,
        connection_id=integration.connection_id,  # type: ignore[arg-type]
        blueprint_id=integration.blueprint_id,  # type: ignore[arg-type]
        pipeline_id=integration.last_pipeline_id,
    )


def _run_devlake_sync_job(
    *,
    job_id: str,
    provider_id: int,
    full_sync: bool,
    skip_collectors: bool,
) -> None:
    _set_sync_job_state(job_id, status="running")
    with Session(engine) as session:
        try:
            provider = _get_devlake_provider_or_404(session, provider_id)
            integration = _get_or_create_integration(session, provider_id)
            result = _sync_provider_to_devlake(
                session=session,
                provider=provider,
                integration=integration,
                full_sync=full_sync,
                skip_collectors=skip_collectors,
            )
            _set_sync_job_state(
                job_id,
                status="succeeded",
                finished_at=_now_iso(),
                result=result.model_dump(),
                error=None,
            )
        except Exception as exc:  # noqa: BLE001
            # Best-effort persistence for visibility/retry UX.
            try:
                provider = session.get(GitProvider, provider_id)
                if provider:
                    integration = _get_or_create_integration(session, provider_id)
                    integration.last_sync_status = "failed"
                    integration.last_sync_error = str(exc)
                    integration.last_synced_at = datetime.now(timezone.utc)
                    integration.updated_at = datetime.now(timezone.utc)
                    session.add(integration)
                    session.commit()
            except Exception:
                pass

            _set_sync_job_state(
                job_id,
                status="failed",
                finished_at=_now_iso(),
                error=str(exc),
            )


@app.get(
    "/api/git-providers/{provider_id}/devlake",
    response_model=DevLakeIntegrationPublic,
)
def get_devlake_integration(
    provider_id: int,
    session: SessionDep,
) -> DevLakeIntegrationPublic:
    _get_devlake_provider_or_404(session, provider_id)
    row = _get_or_create_integration(session, provider_id)
    return _integration_to_public(row)


@app.put(
    "/api/git-providers/{provider_id}/devlake",
    response_model=DevLakeIntegrationPublic,
)
def upsert_devlake_integration(
    provider_id: int,
    payload: DevLakeIntegrationUpdate,
    session: SessionDep,
) -> DevLakeIntegrationPublic:
    provider = _get_devlake_provider_or_404(session, provider_id)
    row = _get_or_create_integration(session, provider_id)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)

    # Create the DevLake connection as soon as config is saved so callers can
    # list remote scopes immediately without a separate /sync bootstrap step.
    plugin_name, _ = _ensure_devlake_connection(
        provider=provider,
        integration=row,
    )
    row.plugin_name = plugin_name
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _integration_to_public(row)


@app.get(
    "/api/git-providers/{provider_id}/devlake/remote-scopes",
    response_model=DevLakeRemoteScopesResponse,
)
def list_devlake_remote_scopes(
    provider_id: int,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
    search_term: str | None = None,
) -> DevLakeRemoteScopesResponse:
    provider = _get_devlake_provider_or_404(session, provider_id)
    row = _get_or_create_integration(session, provider_id)
    plugin_name, client = _ensure_devlake_connection(
        provider=provider,
        integration=row,
    )
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()

    raw = client.list_remote_scopes(
        plugin_name,
        row.connection_id,
        page=page,
        page_size=page_size,
        search_term=search_term,
    )

    scopes = []
    children = raw.get("children") or raw.get("scopes") or []
    if isinstance(children, list):
        for item in children:
            if isinstance(item, dict):
                scopes.append(item)

    count = raw.get("count")
    if not isinstance(count, int):
        count = len(scopes)

    return DevLakeRemoteScopesResponse(scopes=scopes, count=count)


@app.post(
    "/api/git-providers/{provider_id}/devlake/validate",
    response_model=DevLakeValidationResponse,
)
def validate_devlake_integration(
    provider_id: int,
    session: SessionDep,
) -> DevLakeValidationResponse:
    """Preflight-check DevLake credentials/connectivity without triggering sync."""
    provider = _get_devlake_provider_or_404(session, provider_id)
    row = _get_or_create_integration(session, provider_id)
    plugin_name, client = _ensure_devlake_connection(
        provider=provider,
        integration=row,
    )

    # Light connectivity probe: one-page remote scope call.
    raw = client.list_remote_scopes(
        plugin_name,
        row.connection_id,  # type: ignore[arg-type]
        page=1,
        page_size=1,
    )
    children = raw.get("children") or raw.get("scopes") or []
    scope_count = len(children) if isinstance(children, list) else 0

    row.plugin_name = plugin_name
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()

    return DevLakeValidationResponse(
        success=True,
        plugin_name=plugin_name,
        connection_id=row.connection_id,  # type: ignore[arg-type]
        remote_scope_count=scope_count,
        message="DevLake connection is valid and remote scopes are reachable",
    )


@app.post(
    "/api/git-providers/{provider_id}/devlake/sync",
    response_model=DevLakeSyncAcceptedResponse,
)
def sync_git_provider_to_devlake(
    provider_id: int,
    payload: DevLakeSyncRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> DevLakeSyncAcceptedResponse:
    # Fast fail for not-found providers before queueing.
    _get_devlake_provider_or_404(session, provider_id)

    job_id = str(uuid.uuid4())
    _set_sync_job_state(
        job_id,
        job_id=job_id,
        provider_id=provider_id,
        status="queued",
        started_at=_now_iso(),
        finished_at=None,
        result=None,
        error=None,
    )
    background_tasks.add_task(
        _run_devlake_sync_job,
        job_id=job_id,
        provider_id=provider_id,
        full_sync=payload.full_sync,
        skip_collectors=payload.skip_collectors,
    )
    return DevLakeSyncAcceptedResponse(job_id=job_id, status="queued")


@app.get(
    "/api/git-providers/{provider_id}/devlake/sync-jobs/{job_id}",
    response_model=DevLakeSyncJobStatusResponse,
)
def get_devlake_sync_job_status(
    provider_id: int,
    job_id: str,
    session: SessionDep,
) -> DevLakeSyncJobStatusResponse:
    # Keep provider 404 behavior consistent with other DevLake endpoints.
    _get_devlake_provider_or_404(session, provider_id)

    with _devlake_sync_jobs_lock:
        record = _devlake_sync_jobs.get(job_id)
        if not record or record.get("provider_id") != provider_id:
            raise HTTPException(status_code=404, detail="Sync job not found")

    result_payload = record.get("result")
    result = DevLakeSyncResponse(**result_payload) if isinstance(result_payload, dict) else None
    return DevLakeSyncJobStatusResponse(
        job_id=record["job_id"],
        status=record["status"],
        provider_id=record["provider_id"],
        started_at=record["started_at"],
        finished_at=record.get("finished_at"),
        result=result,
        error=record.get("error"),
    )


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
# Token Limits API
# =============================================================================

# Default values from configuration.toml
DEFAULT_TOKEN_LIMITS = {
    "max_description_tokens": 500,
    "max_commits_tokens": 500,
    "max_model_tokens": 32000,
    "custom_model_max_tokens": 32000,
}


class TokenLimits(BaseModel):
    """Token limits configuration model."""
    max_description_tokens: int = 500
    max_commits_tokens: int = 500
    max_model_tokens: int = 32000
    custom_model_max_tokens: int = 32000


class TokenLimitsUpdate(BaseModel):
    """Model for updating token limits."""
    max_description_tokens: int | None = None
    max_commits_tokens: int | None = None
    max_model_tokens: int | None = None
    custom_model_max_tokens: int | None = None


def get_or_create_default_config(session: Session) -> PRAgentConfig:
    """Get the default PR Agent config, creating one if it doesn't exist."""
    statement = select(PRAgentConfig).where(PRAgentConfig.is_default == True)
    config = session.exec(statement).first()

    if not config:
        # Create a default config with token limits from configuration.toml
        config = PRAgentConfig(
            name="Default Configuration",
            is_active=True,
            is_default=True,
            max_description_tokens=DEFAULT_TOKEN_LIMITS["max_description_tokens"],
            max_commits_tokens=DEFAULT_TOKEN_LIMITS["max_commits_tokens"],
            max_model_tokens=DEFAULT_TOKEN_LIMITS["max_model_tokens"],
            custom_model_max_tokens=DEFAULT_TOKEN_LIMITS["custom_model_max_tokens"],
        )
        session.add(config)
        session.commit()
        session.refresh(config)
        get_logger().info("Created default PR Agent configuration")

    return config


@app.get("/api/token-limits", response_model=TokenLimits)
def get_token_limits(session: SessionDep) -> TokenLimits:
    """Get current token limits from the default configuration."""
    config = get_or_create_default_config(session)
    return TokenLimits(
        max_description_tokens=config.max_description_tokens,
        max_commits_tokens=config.max_commits_tokens,
        max_model_tokens=config.max_model_tokens,
        custom_model_max_tokens=config.custom_model_max_tokens,
    )


@app.put("/api/token-limits", response_model=TokenLimits)
def update_token_limits(
    limits: TokenLimitsUpdate,
    session: SessionDep,
) -> TokenLimits:
    """Update token limits in the default configuration."""
    config = get_or_create_default_config(session)

    # Update only provided fields
    update_data = limits.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(config, key, value)

    config.updated_at = datetime.now(timezone.utc)
    session.add(config)
    session.commit()
    session.refresh(config)

    get_logger().info(f"Updated token limits: {update_data}")

    return TokenLimits(
        max_description_tokens=config.max_description_tokens,
        max_commits_tokens=config.max_commits_tokens,
        max_model_tokens=config.max_model_tokens,
        custom_model_max_tokens=config.custom_model_max_tokens,
    )


@app.get("/api/token-limits/defaults", response_model=TokenLimits)
def get_default_token_limits() -> TokenLimits:
    """Get the default token limits from configuration.toml."""
    return TokenLimits(**DEFAULT_TOKEN_LIMITS)


@app.post("/api/token-limits/reset", response_model=TokenLimits)
def reset_token_limits(session: SessionDep) -> TokenLimits:
    """Reset token limits to default values from configuration.toml."""
    config = get_or_create_default_config(session)

    config.max_description_tokens = DEFAULT_TOKEN_LIMITS["max_description_tokens"]
    config.max_commits_tokens = DEFAULT_TOKEN_LIMITS["max_commits_tokens"]
    config.max_model_tokens = DEFAULT_TOKEN_LIMITS["max_model_tokens"]
    config.custom_model_max_tokens = DEFAULT_TOKEN_LIMITS["custom_model_max_tokens"]
    config.updated_at = datetime.now(timezone.utc)

    session.add(config)
    session.commit()
    session.refresh(config)

    get_logger().info("Reset token limits to defaults")

    return TokenLimits(**DEFAULT_TOKEN_LIMITS)


# =============================================================================
# Learnings API (Mem0 knowledge base)
# =============================================================================

class LearningPublic(BaseModel):
    """Public representation of a stored learning/memory."""

    id: str | None = None
    repo: str | None = None
    text: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = {}


class LearningsListResponse(BaseModel):
    """Response payload for listing learnings."""

    enabled: bool
    total: int
    items: list[LearningPublic]
    repos: list[str] = []


def _record_to_public(record: LearningRecord) -> LearningPublic:
    return LearningPublic(
        id=record.id,
        repo=record.repo,
        text=record.text,
        created_at=record.created_at,
        metadata=record.metadata or {},
    )


@app.get("/api/learnings", response_model=LearningsListResponse)
def list_learnings(
    repo: Annotated[str | None, Query(description="Filter by repository full name (e.g. org/repo)")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> LearningsListResponse:
    """List learnings stored in the knowledge base (mem0).

    Returns the records captured from PR review feedback. When `repo` is
    provided, only learnings for that repository are returned.
    """
    provider = get_memory_provider()
    if not provider.is_enabled():
        return LearningsListResponse(enabled=False, total=0, items=[], repos=[])

    try:
        records = provider.list_all_learnings(repo_full_name=repo, limit=limit)
        # `total` must reflect the full population, not just the page the UI
        # asked for, otherwise homepage counters that pass a tiny limit will
        # under-report (see regression where homepage showed 1 vs. /learnings
        # showing 11).
        total = provider.count_learnings(repo_full_name=repo)
        repos = provider.list_repos()
    except Exception as e:  # defensive: never crash the endpoint
        get_logger().warning(f"Failed to load learnings: {e}")
        raise HTTPException(status_code=500, detail="Failed to load learnings") from e

    return LearningsListResponse(
        enabled=True,
        total=total,
        items=[_record_to_public(r) for r in records],
        repos=repos,
    )


@app.get("/api/learnings/repos")
def list_learning_repos() -> dict[str, Any]:
    """Return the list of repositories that have stored learnings."""
    provider = get_memory_provider()
    if not provider.is_enabled():
        return {"enabled": False, "repos": []}
    return {"enabled": True, "repos": provider.list_repos()}


@app.delete("/api/learnings/{learning_id}")
def delete_learning(learning_id: str) -> dict[str, str]:
    """Delete a single learning by its mem0 id."""
    provider = get_memory_provider()
    if not provider.is_enabled():
        raise HTTPException(status_code=400, detail="Knowledge base is disabled")

    if not provider.delete_learning(learning_id):
        raise HTTPException(status_code=404, detail="Learning not found or could not be deleted")

    get_logger().info(f"Deleted learning {learning_id}")
    return {"status": "deleted", "id": learning_id}


# =============================================================================
# PR review activity API
#
# Reads the append-only audit log populated by `PRAgent._handle_request`.
# The `stats` endpoint powers the dashboard's "Reviewed PRs" card; the list
# endpoint is intended for a future activity drawer / per-repo view.
# =============================================================================


class PRReviewActivityListResponse(BaseModel):
    total: int
    items: list[PRReviewActivityPublic]


@app.get("/api/pr-review-activities/stats", response_model=PRReviewActivityStats)
def pr_review_activity_stats(
    repo: Annotated[str | None, Query(description="Restrict counters to a single repo (owner/repo)")] = None,
) -> PRReviewActivityStats:
    """Aggregated counters across the PR review audit log."""
    return review_activity_service.get_stats(repo=repo)


@app.get("/api/pr-review-activities", response_model=PRReviewActivityListResponse)
def list_pr_review_activities(
    repo: Annotated[str | None, Query(description="Filter by repo (owner/repo)")] = None,
    tool: Annotated[str | None, Query(description="Filter by canonical tool name (review, improve, ...)")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PRReviewActivityListResponse:
    """Return the newest activity rows matching the filters."""
    rows = review_activity_service.list_activities(repo=repo, tool=tool, limit=limit)
    return PRReviewActivityListResponse(
        total=len(rows),
        items=[
            PRReviewActivityPublic(
                id=r.id,  # type: ignore[arg-type]
                provider_type=r.provider_type,
                repo=r.repo,
                pr_number=r.pr_number,
                pr_url=r.pr_url,
                tool=r.tool,
                triggered_by=r.triggered_by,
                success=r.success,
                duration_ms=r.duration_ms,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )


# =============================================================================
# Automation API (per-provider pr_commands / push_commands / toggles)
#
# Lets the Dashboard edit the "auto-review when a PR is opened" behavior that
# previously lived in .pr_agent.toml. Values are stored in JSON columns on the
# default PRAgentConfig row and pushed into Dynaconf at webhook time by
# `pr_agent.secret_providers.postgres_provider.apply_automation_config_to_settings`.
# =============================================================================

# Keys the Dashboard is allowed to manage per provider. Anything outside this
# set is preserved in the JSON column but not exposed.
#
# Note: `disable_auto_feedback` is intentionally NOT in this set — it lives on
# the `pr_agent_configs.disable_auto_feedback` column (added in Alembic
# revision 0002) and is handled separately below.
AUTOMATION_ALLOWED_KEYS: tuple[str, ...] = (
    "pr_commands",
    "push_commands",
    "handle_push_trigger",
    "handle_pr_actions",
    "feedback_on_draft_pr",
)

# Default values surfaced when a provider has no stored config yet. Kept in
# sync with pr_agent/settings/configuration.toml so the UI shows the actual
# runtime defaults.
AUTOMATION_DEFAULTS: dict[str, dict[str, Any]] = {
    "github_app": {
        "pr_commands": [
            "/describe --pr_description.final_update_message=false",
            "/review",
            "/improve",
        ],
        "push_commands": ["/describe", "/review"],
        "handle_push_trigger": False,
        "handle_pr_actions": ["opened", "reopened", "ready_for_review"],
        "feedback_on_draft_pr": False,
    },
    "gitlab": {
        "pr_commands": [
            "/describe --pr_description.final_update_message=false",
            "/review",
            "/improve",
        ],
        "push_commands": ["/describe", "/review"],
        "handle_push_trigger": False,
    },
    "bitbucket_app": {
        "pr_commands": [
            "/describe --pr_description.final_update_message=false",
            "/review",
            "/improve --pr_code_suggestions.commitable_code_suggestions=true",
        ],
        "push_commands": ["/describe", "/review"],
        "handle_push_trigger": False,
    },
    "azure_devops": {
        "pr_commands": ["/describe", "/review", "/improve"],
    },
    "gitea": {
        "pr_commands": ["/describe", "/review", "/improve"],
        "push_commands": ["/describe", "/review"],
        "handle_push_trigger": False,
    },
}

# Mapping from API key -> PRAgentConfig JSON column name.
AUTOMATION_COLUMN_MAP: dict[str, str] = {
    "github_app": "github_app_config",
    "gitlab": "gitlab_config",
    "bitbucket_app": "bitbucket_app_config",
    "azure_devops": "azure_devops_config",
    "gitea": "gitea_config",
}


class ProviderAutomationConfig(BaseModel):
    """Automation config for a single git provider."""

    pr_commands: list[str] = []
    push_commands: list[str] = []
    handle_push_trigger: bool = False
    handle_pr_actions: list[str] | None = None
    feedback_on_draft_pr: bool | None = None
    disable_auto_feedback: bool | None = None


class AutomationConfigResponse(BaseModel):
    """Full automation config surfaced to the Dashboard."""

    disable_auto_feedback: bool = False
    github_app: ProviderAutomationConfig
    gitlab: ProviderAutomationConfig
    bitbucket_app: ProviderAutomationConfig
    azure_devops: ProviderAutomationConfig
    gitea: ProviderAutomationConfig


class AutomationConfigUpdate(BaseModel):
    """Partial update for automation config. Missing keys leave values unchanged."""

    disable_auto_feedback: bool | None = None
    github_app: ProviderAutomationConfig | None = None
    gitlab: ProviderAutomationConfig | None = None
    bitbucket_app: ProviderAutomationConfig | None = None
    azure_devops: ProviderAutomationConfig | None = None
    gitea: ProviderAutomationConfig | None = None


def _provider_config_from_column(
    stored: dict[str, Any] | None,
    defaults: dict[str, Any],
) -> ProviderAutomationConfig:
    """Merge stored JSON column with per-provider defaults into the API shape."""
    merged = dict(defaults)
    if stored:
        for key, value in stored.items():
            if key in AUTOMATION_ALLOWED_KEYS:
                merged[key] = value
    return ProviderAutomationConfig(**{k: merged.get(k) for k in merged})


def _build_automation_response(config: PRAgentConfig) -> AutomationConfigResponse:
    """Compose the API response from a PRAgentConfig row."""
    return AutomationConfigResponse(
        disable_auto_feedback=bool(config.disable_auto_feedback),
        github_app=_provider_config_from_column(
            config.github_app_config, AUTOMATION_DEFAULTS["github_app"]
        ),
        gitlab=_provider_config_from_column(
            config.gitlab_config, AUTOMATION_DEFAULTS["gitlab"]
        ),
        bitbucket_app=_provider_config_from_column(
            config.bitbucket_app_config, AUTOMATION_DEFAULTS["bitbucket_app"]
        ),
        azure_devops=_provider_config_from_column(
            config.azure_devops_config, AUTOMATION_DEFAULTS["azure_devops"]
        ),
        gitea=_provider_config_from_column(
            config.gitea_config, AUTOMATION_DEFAULTS["gitea"]
        ),
    )


def _merge_provider_update(
    existing: dict[str, Any] | None,
    update: ProviderAutomationConfig,
) -> dict[str, Any]:
    """Produce the new JSON payload for a provider column.

    Only keys in `AUTOMATION_ALLOWED_KEYS` are written; unknown keys in the
    existing JSON are preserved verbatim so ad-hoc settings stored outside the
    dashboard are not clobbered.
    """
    merged: dict[str, Any] = dict(existing or {})
    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        if key in AUTOMATION_ALLOWED_KEYS:
            merged[key] = value
    return merged


@app.get("/api/automation", response_model=AutomationConfigResponse)
def get_automation_config(session: SessionDep) -> AutomationConfigResponse:
    """Return the current automation config for every supported provider."""
    config = get_or_create_default_config(session)
    return _build_automation_response(config)


@app.put("/api/automation", response_model=AutomationConfigResponse)
def update_automation_config(
    update: AutomationConfigUpdate,
    session: SessionDep,
) -> AutomationConfigResponse:
    """Persist automation config changes and invalidate the webhook cache."""
    config = get_or_create_default_config(session)

    if update.disable_auto_feedback is not None:
        config.disable_auto_feedback = update.disable_auto_feedback

    provider_updates: dict[str, ProviderAutomationConfig | None] = {
        "github_app": update.github_app,
        "gitlab": update.gitlab,
        "bitbucket_app": update.bitbucket_app,
        "azure_devops": update.azure_devops,
        "gitea": update.gitea,
    }

    for api_key, provider_update in provider_updates.items():
        if provider_update is None:
            continue
        column = AUTOMATION_COLUMN_MAP[api_key]
        existing = getattr(config, column, None)
        new_value = _merge_provider_update(existing, provider_update)
        setattr(config, column, new_value)

    config.updated_at = datetime.now(timezone.utc)
    session.add(config)
    session.commit()
    session.refresh(config)

    # Best-effort cache bust so a running webhook service picks up changes on
    # the next delivery instead of waiting for the TTL window to expire.
    try:
        from pr_agent.secret_providers.postgres_provider import (
            invalidate_postgres_config_cache,
        )

        invalidate_postgres_config_cache()
    except Exception:  # defensive: never block the save
        pass

    get_logger().info("Updated automation config")
    return _build_automation_response(config)


@app.post("/api/automation/reload")
def reload_automation_config() -> dict[str, str]:
    """Force the webhook service to re-read automation config on its next call."""
    try:
        from pr_agent.secret_providers.postgres_provider import (
            invalidate_postgres_config_cache,
        )

        invalidate_postgres_config_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to invalidate cache") from e
    return {"status": "ok"}


# =============================================================================
# Knowledge-base API (Stage 2)
#
# CRUD over the `knowledge_base_config` JSON column on the default
# PRAgentConfig row. Runtime code (github_app, pr_learn, ...) still reads
# KNOWLEDGE_BASE.* from Dynaconf; the postgres_provider overlays this JSON
# on top of the TOML defaults so the Dashboard becomes the source of truth
# without breaking CLI / GitHub-Action callers.
# =============================================================================

# Keys the Dashboard manages. Anything outside this allow-list that happens to
# be in the JSON column (e.g. values written by a future admin tool) is kept
# verbatim but neither surfaced nor overwritten. Infra-level keys
# (`chroma_path`, `embedding_model`, `provider`, `scope`, ...) are intentionally
# excluded - they belong in configuration.toml / deploy config.
KNOWLEDGE_BASE_ALLOWED_KEYS: tuple[str, ...] = (
    "enabled",
    "explicit_learn_enabled",
    "learn_command",
    "extraction_rules",
    "apply_to_review",
    "max_retrieved_learnings",
    "max_summary_chars",
    "duplicate_threshold",
    "capture_from_pr_comments",
    "require_agent_mention",
)

# Defaults surfaced when the DB row is NULL or missing a key. Kept in sync
# with `[knowledge_base]` in pr_agent/settings/configuration.toml.
KNOWLEDGE_BASE_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "explicit_learn_enabled": True,
    "learn_command": "/learn",
    "extraction_rules": [],
    "apply_to_review": True,
    "max_retrieved_learnings": 5,
    "max_summary_chars": 1200,
    "duplicate_threshold": 0.9,
    "capture_from_pr_comments": False,
    "require_agent_mention": True,
}

# Template rules auto-seeded when an admin disables `explicit_learn_enabled`
# with an empty rule list. Mirrors `learning_extractor.PREFERENCE_MARKERS` so
# passive capture still produces useful hits even if the operator never
# configures the rules manually.
KNOWLEDGE_BASE_DEFAULT_RULES: tuple[str, ...] = (
    "we prefer",
    "in this project",
    "in this repo",
    "we always",
    "we never",
    "our standard",
    "our convention",
    "please avoid",
    "do not suggest",
    "should use",
    "shouldn't use",
)


class KnowledgeBaseConfig(BaseModel):
    """Full knowledge-base config surfaced to the Dashboard."""

    enabled: bool = False
    explicit_learn_enabled: bool = True
    learn_command: str = "/learn"
    extraction_rules: list[str] = []
    apply_to_review: bool = True
    max_retrieved_learnings: int = 5
    max_summary_chars: int = 1200
    duplicate_threshold: float = 0.9
    capture_from_pr_comments: bool = False
    require_agent_mention: bool = True


class KnowledgeBaseConfigUpdate(BaseModel):
    """Partial update for knowledge-base config. Missing keys leave values unchanged."""

    enabled: bool | None = None
    explicit_learn_enabled: bool | None = None
    learn_command: str | None = None
    extraction_rules: list[str] | None = None
    apply_to_review: bool | None = None
    max_retrieved_learnings: int | None = None
    max_summary_chars: int | None = None
    duplicate_threshold: float | None = None
    capture_from_pr_comments: bool | None = None
    require_agent_mention: bool | None = None


def _build_knowledge_base_response(config: PRAgentConfig) -> KnowledgeBaseConfig:
    """Compose the API response by merging stored JSON with defaults."""
    merged: dict[str, Any] = dict(KNOWLEDGE_BASE_DEFAULTS)
    stored = config.knowledge_base_config or {}
    for key in KNOWLEDGE_BASE_ALLOWED_KEYS:
        if key in stored:
            merged[key] = stored[key]
    # Normalise extraction_rules into a clean list[str] so callers never see
    # stray types coming back from historical JSON.
    raw_rules = merged.get("extraction_rules") or []
    if isinstance(raw_rules, (list, tuple)):
        merged["extraction_rules"] = [str(r) for r in raw_rules if isinstance(r, str)]
    else:
        merged["extraction_rules"] = []
    return KnowledgeBaseConfig(**merged)


def _merge_knowledge_base_update(
    existing: dict[str, Any] | None,
    update: KnowledgeBaseConfigUpdate,
) -> dict[str, Any]:
    """Produce the new JSON payload by overlaying the allow-listed fields.

    Unknown keys in ``existing`` are preserved (forward-compat). Values written
    by this function are normalised (lists coerced to ``list[str]``, strings
    stripped) so the UI can't push misshapen data into the DB.
    """
    merged: dict[str, Any] = dict(existing or {})
    update_dict = update.model_dump(exclude_none=True)

    for key, value in update_dict.items():
        if key not in KNOWLEDGE_BASE_ALLOWED_KEYS:
            continue
        if key == "extraction_rules":
            if not isinstance(value, list):
                continue
            merged[key] = [str(v).strip() for v in value if isinstance(v, str) and v.strip()]
        elif key == "learn_command":
            merged[key] = str(value).strip() or "/learn"
        else:
            merged[key] = value

    # Safety net: an operator who turns explicit_learn off without defining
    # any rules would otherwise silently stop capturing anything. Prefill the
    # template markers so the system keeps working; operators can always delete
    # rules they don't want. Done *after* the regular merge so an explicit
    # empty list on an already-disabled config stays empty unless the user
    # just-now flipped the toggle - which we detect by checking the pre-update
    # row through the caller's `existing` snapshot.
    if merged.get("explicit_learn_enabled") is False and not merged.get("extraction_rules"):
        previously_disabled = bool(existing) and existing.get("explicit_learn_enabled") is False
        if not previously_disabled:
            merged["extraction_rules"] = list(KNOWLEDGE_BASE_DEFAULT_RULES)

    return merged


@app.get("/api/knowledge-base", response_model=KnowledgeBaseConfig)
def get_knowledge_base_config(session: SessionDep) -> KnowledgeBaseConfig:
    """Return the current knowledge-base config, merged with TOML defaults."""
    config = get_or_create_default_config(session)
    return _build_knowledge_base_response(config)


@app.put("/api/knowledge-base", response_model=KnowledgeBaseConfig)
def update_knowledge_base_config(
    update: KnowledgeBaseConfigUpdate,
    session: SessionDep,
) -> KnowledgeBaseConfig:
    """Persist knowledge-base config changes and invalidate the webhook cache."""
    config = get_or_create_default_config(session)

    existing = dict(config.knowledge_base_config or {})
    config.knowledge_base_config = _merge_knowledge_base_update(existing, update)
    config.updated_at = datetime.now(timezone.utc)
    session.add(config)
    session.commit()
    session.refresh(config)

    # Best-effort cache bust - webhook picks up the change on the next delivery.
    try:
        from pr_agent.secret_providers.postgres_provider import (
            invalidate_postgres_config_cache,
        )

        invalidate_postgres_config_cache()
    except Exception:
        pass

    get_logger().info("Updated knowledge-base config")
    return _build_knowledge_base_response(config)


@app.post("/api/knowledge-base/reload")
def reload_knowledge_base_config() -> dict[str, str]:
    """Force the webhook service to re-read knowledge-base config on its next call."""
    try:
        from pr_agent.secret_providers.postgres_provider import (
            invalidate_postgres_config_cache,
        )

        invalidate_postgres_config_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to invalidate cache") from e
    return {"status": "ok"}


# =============================================================================
# Webhook registry (P1)
#
# CRUD over `webhook_registrations` + provider-side actions
# (register / unregister / test / deliveries). The provider adapter lives in
# `pr_agent.servers.webhook_registry`; this layer just glues HTTP to DB.
# =============================================================================


def _webhook_to_public(record: WebhookRegistration) -> WebhookRegistrationPublic:
    """Project a DB row into the public response shape (no raw secret)."""
    return WebhookRegistrationPublic(
        id=record.id,  # type: ignore[arg-type]
        git_provider_id=record.git_provider_id,
        repo=record.repo,
        target_url=record.target_url,
        events=list(record.events or []),
        active=record.active,
        content_type=record.content_type,
        insecure_ssl=record.insecure_ssl,
        status=record.status,
        external_id=record.external_id,
        has_secret=bool(record.secret),
        last_delivery_at=record.last_delivery_at,
        last_status_code=record.last_status_code,
        last_error=record.last_error,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _get_provider_or_404(session: Session, provider_id: int) -> GitProvider:
    provider = session.get(GitProvider, provider_id)
    if not provider:
        raise HTTPException(
            status_code=404, detail=f"Git provider {provider_id} not found"
        )
    return provider


def _get_webhook_or_404(
    session: Session, webhook_id: int
) -> WebhookRegistration:
    record = session.get(WebhookRegistration, webhook_id)
    if not record:
        raise HTTPException(
            status_code=404, detail=f"Webhook {webhook_id} not found"
        )
    return record


class WebhookEndpointInfo(BaseModel):
    """Self-reported webhook URL + recommended event list per provider type."""

    provider_type: str
    path: str
    default_events: list[str]
    note: str | None = None


def _compute_endpoint_base() -> str:
    """Derive the externally-reachable PR-Agent base URL from env.

    Falls back to empty string so the Dashboard can display `<base>/path`
    even when the admin hasn't set one (they then just copy the path part).
    """
    return (os.environ.get("PR_AGENT_PUBLIC_URL") or "").rstrip("/")


@app.get("/api/webhooks/endpoints", response_model=list[WebhookEndpointInfo])
def list_webhook_endpoints() -> list[WebhookEndpointInfo]:
    """Return the webhook paths this PR-Agent deployment exposes."""
    base = _compute_endpoint_base()

    def _full(path: str) -> str:
        return f"{base}{path}" if base else path

    return [
        WebhookEndpointInfo(
            provider_type=GitProviderType.github.value,
            path=_full("/api/v1/github_webhooks"),
            default_events=["pull_request", "push", "issue_comment"],
            note="For user PAT deployments. GitHub Apps deliver events via the App-level webhook.",
        ),
        WebhookEndpointInfo(
            provider_type=GitProviderType.gitlab.value,
            path=_full("/webhook"),
            default_events=["Merge request events", "Push events", "Note events"],
        ),
        WebhookEndpointInfo(
            provider_type=GitProviderType.bitbucket.value,
            path=_full("/"),
            default_events=["pullrequest:created", "pullrequest:updated"],
        ),
        WebhookEndpointInfo(
            provider_type=GitProviderType.gitea.value,
            path=_full("/api/v1/gitea_webhooks"),
            default_events=["pull_request", "push"],
        ),
    ]


@app.get("/api/webhooks", response_model=list[WebhookRegistrationPublic])
def list_webhooks(
    session: SessionDep,
    git_provider_id: int | None = Query(
        default=None, description="Filter by git provider id"
    ),
    repo: str | None = Query(
        default=None, description="Filter by repo (exact match)"
    ),
) -> list[WebhookRegistrationPublic]:
    """List webhook registrations, optionally filtered by provider or repo."""
    stmt = select(WebhookRegistration)
    if git_provider_id is not None:
        stmt = stmt.where(WebhookRegistration.git_provider_id == git_provider_id)
    if repo:
        stmt = stmt.where(WebhookRegistration.repo == repo)
    rows = session.exec(stmt.order_by(WebhookRegistration.id.desc())).all()
    return [_webhook_to_public(r) for r in rows]


@app.get(
    "/api/webhooks/{webhook_id}", response_model=WebhookRegistrationPublic
)
def get_webhook(
    webhook_id: int, session: SessionDep
) -> WebhookRegistrationPublic:
    return _webhook_to_public(_get_webhook_or_404(session, webhook_id))


@app.post(
    "/api/webhooks",
    response_model=WebhookRegistrationPublic,
    status_code=201,
)
def create_webhook(
    payload: WebhookRegistrationCreate, session: SessionDep
) -> WebhookRegistrationPublic:
    """Create a webhook registration row in 'draft' state (not yet registered)."""
    # Importing here keeps the top of api.py slimmer and avoids any import
    # cycle with the webhook_registry module.
    from pr_agent.servers.webhook_registry import generate_webhook_secret

    _get_provider_or_404(session, payload.git_provider_id)

    record = WebhookRegistration(
        git_provider_id=payload.git_provider_id,
        repo=payload.repo,
        target_url=payload.target_url,
        events=payload.events,
        active=payload.active,
        content_type=payload.content_type,
        insecure_ssl=payload.insecure_ssl,
        # If the caller didn't supply a secret, mint one so HMAC verification
        # works out-of-the-box when they register on the provider.
        secret=payload.secret or generate_webhook_secret(),
        status=WebhookRegistrationStatus.draft,
    )
    session.add(record)
    try:
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        # Most common cause: uq_webhook_registrations_provider_repo_url violation.
        raise HTTPException(
            status_code=409,
            detail="A webhook for this provider + repo + URL already exists",
        ) from exc
    session.refresh(record)
    return _webhook_to_public(record)


@app.put(
    "/api/webhooks/{webhook_id}", response_model=WebhookRegistrationPublic
)
def update_webhook(
    webhook_id: int,
    payload: WebhookRegistrationUpdate,
    session: SessionDep,
) -> WebhookRegistrationPublic:
    record = _get_webhook_or_404(session, webhook_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(record, key, value)
    record.updated_at = datetime.now(timezone.utc)
    session.add(record)
    try:
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Update would violate uniqueness on (provider, repo, url)",
        ) from exc
    session.refresh(record)
    return _webhook_to_public(record)


@app.delete("/api/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: int,
    session: SessionDep,
    also_unregister: bool = Query(
        default=True,
        description="If True, attempt to delete the webhook on the provider first",
    ),
) -> None:
    """Delete a webhook row. Optionally calls the provider first to unregister."""
    from pr_agent.servers.webhook_registry import (
        WebhookRegistryError,
        get_adapter,
    )

    record = _get_webhook_or_404(session, webhook_id)

    if also_unregister and record.external_id:
        provider = _get_provider_or_404(session, record.git_provider_id)
        try:
            get_adapter(provider.type).unregister(provider, record)
        except WebhookRegistryError as exc:
            # Surface the error but let the client choose to retry with
            # also_unregister=false to force-delete the local row.
            raise HTTPException(
                status_code=exc.status_code, detail=str(exc)
            ) from exc

    session.delete(record)
    session.commit()


@app.post(
    "/api/webhooks/{webhook_id}/register",
    response_model=WebhookRegistrationPublic,
)
def register_webhook(
    webhook_id: int, session: SessionDep
) -> WebhookRegistrationPublic:
    """Create the webhook on the remote provider."""
    from pr_agent.servers.webhook_registry import (
        WebhookRegistryError,
        get_adapter,
    )

    record = _get_webhook_or_404(session, webhook_id)
    provider = _get_provider_or_404(session, record.git_provider_id)

    try:
        result = get_adapter(provider.type).register(provider, record)
    except WebhookRegistryError as exc:
        record.status = WebhookRegistrationStatus.failed
        record.last_error = str(exc)
        record.updated_at = datetime.now(timezone.utc)
        session.add(record)
        session.commit()
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc

    record.external_id = result.external_id or record.external_id
    record.status = WebhookRegistrationStatus.registered
    record.last_error = None
    record.last_status_code = result.status_code
    record.updated_at = datetime.now(timezone.utc)
    session.add(record)
    session.commit()
    session.refresh(record)
    return _webhook_to_public(record)


@app.post(
    "/api/webhooks/{webhook_id}/unregister",
    response_model=WebhookRegistrationPublic,
)
def unregister_webhook(
    webhook_id: int, session: SessionDep
) -> WebhookRegistrationPublic:
    """Delete the webhook on the remote provider (keep the local row)."""
    from pr_agent.servers.webhook_registry import (
        WebhookRegistryError,
        get_adapter,
    )

    record = _get_webhook_or_404(session, webhook_id)
    provider = _get_provider_or_404(session, record.git_provider_id)

    try:
        result = get_adapter(provider.type).unregister(provider, record)
    except WebhookRegistryError as exc:
        record.last_error = str(exc)
        record.updated_at = datetime.now(timezone.utc)
        session.add(record)
        session.commit()
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc

    record.external_id = None
    record.status = WebhookRegistrationStatus.deleted
    record.last_error = None
    record.last_status_code = result.status_code
    record.updated_at = datetime.now(timezone.utc)
    session.add(record)
    session.commit()
    session.refresh(record)
    return _webhook_to_public(record)


@app.post("/api/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: int, session: SessionDep) -> dict[str, Any]:
    """Ask the provider to send a test delivery."""
    from pr_agent.servers.webhook_registry import (
        WebhookRegistryError,
        get_adapter,
    )

    record = _get_webhook_or_404(session, webhook_id)
    provider = _get_provider_or_404(session, record.git_provider_id)

    try:
        result = get_adapter(provider.type).test(provider, record)
    except WebhookRegistryError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc

    return {
        "status": "ok",
        "message": result.message,
        "status_code": result.status_code,
    }


@app.get(
    "/api/webhooks/{webhook_id}/deliveries",
    response_model=list[WebhookDelivery],
)
def list_webhook_deliveries(
    webhook_id: int,
    session: SessionDep,
    limit: int = Query(default=30, ge=1, le=100),
) -> list[WebhookDelivery]:
    """Return recent deliveries reported by the provider."""
    from pr_agent.servers.webhook_registry import get_adapter

    record = _get_webhook_or_404(session, webhook_id)
    provider = _get_provider_or_404(session, record.git_provider_id)
    return get_adapter(provider.type).list_deliveries(
        provider, record, limit=limit
    )


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
