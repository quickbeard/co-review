"""
SQLModel models for PR-Agent database.

These models define the schema for git provider credentials storage.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class GitProviderType(str, Enum):
    """Supported git provider types."""
    github = "github"
    gitlab = "gitlab"
    bitbucket = "bitbucket"
    azure_devops = "azure_devops"
    gitea = "gitea"
    gerrit = "gerrit"


class GitHubDeploymentType(str, Enum):
    """GitHub authentication deployment types."""
    user = "user"  # Personal Access Token
    app = "app"    # GitHub App


# =============================================================================
# Base model with common fields
# =============================================================================

class GitProviderBase(SQLModel):
    """Base model for git provider with shared fields."""
    type: GitProviderType = Field(description="Git provider type")
    name: str = Field(min_length=1, max_length=255, description="Display name")
    base_url: Optional[str] = Field(default=None, max_length=500, description="Base URL for self-hosted instances")
    webhook_secret: Optional[str] = Field(default=None, max_length=500, description="Webhook secret for verification")
    is_active: bool = Field(default=True, description="Whether the provider is active")

    # GitHub-specific fields
    deployment_type: Optional[GitHubDeploymentType] = Field(default=None, description="GitHub deployment type (user or app)")


# =============================================================================
# Database model (table)
# =============================================================================

class GitProvider(GitProviderBase, table=True):
    """Git provider database model."""
    __tablename__ = "git_providers"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Credentials (stored encrypted in production)
    access_token: Optional[str] = Field(default=None, max_length=1000, description="Personal access token")
    app_id: Optional[str] = Field(default=None, max_length=100, description="GitHub App ID")
    private_key: Optional[str] = Field(default=None, description="GitHub App private key (PEM format)")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")


# =============================================================================
# API models (for request/response)
# =============================================================================

class GitProviderCreate(GitProviderBase):
    """Model for creating a new git provider."""
    # Credentials
    access_token: Optional[str] = Field(default=None, description="Personal access token")
    app_id: Optional[str] = Field(default=None, description="GitHub App ID")
    private_key: Optional[str] = Field(default=None, description="GitHub App private key")


class GitProviderUpdate(SQLModel):
    """Model for updating an existing git provider."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    base_url: Optional[str] = Field(default=None, max_length=500)
    webhook_secret: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)
    deployment_type: Optional[GitHubDeploymentType] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    app_id: Optional[str] = Field(default=None)
    private_key: Optional[str] = Field(default=None)


class GitProviderPublic(GitProviderBase):
    """Model for public API responses (excludes sensitive fields)."""
    id: int
    created_at: datetime
    updated_at: datetime
