"""
SQLModel models for PR-Agent database.

These models define the schema for git provider credentials, LLM providers,
vector database providers, and PR-Agent configuration storage.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from sqlmodel import Column, Field, SQLModel
from sqlalchemy import JSON


class GitProviderType(str, Enum):
    """Supported git provider types."""
    github = "github"
    gitlab = "gitlab"
    bitbucket = "bitbucket"
    bitbucket_server = "bitbucket_server"
    azure_devops = "azure_devops"
    azure_devops_server = "azure_devops_server"
    gitea = "gitea"
    gerrit = "gerrit"


class GitHubDeploymentType(str, Enum):
    """GitHub authentication deployment types."""
    user = "user"  # Personal Access Token
    app = "app"    # GitHub App


class BitbucketAuthType(str, Enum):
    """Bitbucket authentication types."""
    bearer = "bearer"
    basic = "basic"


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""
    openai = "openai"
    anthropic = "anthropic"
    cohere = "cohere"
    replicate = "replicate"
    groq = "groq"
    xai = "xai"
    huggingface = "huggingface"
    ollama = "ollama"
    vertexai = "vertexai"
    google_ai_studio = "google_ai_studio"
    deepseek = "deepseek"
    deepinfra = "deepinfra"
    azure_openai = "azure_openai"
    azure_ad = "azure_ad"
    openrouter = "openrouter"
    aws_bedrock = "aws_bedrock"
    litellm = "litellm"


class VectorDBType(str, Enum):
    """Supported vector database types for similar issues feature."""
    pinecone = "pinecone"
    qdrant = "qdrant"
    lancedb = "lancedb"


class OpenAIApiType(str, Enum):
    """OpenAI API types."""
    openai = "openai"
    azure = "azure"


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
    is_default: bool = Field(default=False, description="Whether this is the default git provider")

    # GitHub-specific fields
    deployment_type: Optional[GitHubDeploymentType] = Field(default=None, description="GitHub deployment type (user or app)")

    # Bitbucket-specific fields
    auth_type: Optional[BitbucketAuthType] = Field(default=None, description="Bitbucket auth type (bearer or basic)")

    # Azure DevOps-specific fields
    organization: Optional[str] = Field(default=None, max_length=255, description="Azure DevOps organization name")


# =============================================================================
# Database model (table)
# =============================================================================

class GitProvider(GitProviderBase, table=True):
    """Git provider database model."""
    __tablename__ = "git_providers"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Common credentials (stored encrypted in production)
    access_token: Optional[str] = Field(default=None, max_length=1000, description="Personal access token / bearer token")

    # GitHub App-specific credentials
    app_id: Optional[str] = Field(default=None, max_length=100, description="GitHub App ID")
    private_key: Optional[str] = Field(default=None, description="GitHub App private key (PEM format)")

    # Bitbucket-specific credentials
    basic_token: Optional[str] = Field(default=None, max_length=500, description="Bitbucket basic auth token")
    app_key: Optional[str] = Field(default=None, max_length=255, description="Bitbucket Server app key")

    # Azure DevOps-specific credentials
    pat: Optional[str] = Field(default=None, max_length=500, description="Azure DevOps personal access token")
    webhook_username: Optional[str] = Field(default=None, max_length=255, description="Azure DevOps Server webhook username")
    webhook_password: Optional[str] = Field(default=None, max_length=500, description="Azure DevOps Server webhook password")

    # Gerrit-specific credentials
    gerrit_user: Optional[str] = Field(default=None, max_length=255, description="Gerrit user for authentication")
    patch_server_endpoint: Optional[str] = Field(default=None, max_length=500, description="Gerrit patch server endpoint")
    patch_server_token: Optional[str] = Field(default=None, max_length=500, description="Gerrit patch server token")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")


# =============================================================================
# API models (for request/response)
# =============================================================================

class GitProviderCreate(GitProviderBase):
    """Model for creating a new git provider."""
    # Common credentials
    access_token: Optional[str] = Field(default=None, description="Personal access token / bearer token")

    # GitHub App-specific
    app_id: Optional[str] = Field(default=None, description="GitHub App ID")
    private_key: Optional[str] = Field(default=None, description="GitHub App private key")

    # Bitbucket-specific
    basic_token: Optional[str] = Field(default=None, description="Bitbucket basic auth token")
    app_key: Optional[str] = Field(default=None, description="Bitbucket Server app key")

    # Azure DevOps-specific
    pat: Optional[str] = Field(default=None, description="Azure DevOps personal access token")
    webhook_username: Optional[str] = Field(default=None, description="Azure DevOps Server webhook username")
    webhook_password: Optional[str] = Field(default=None, description="Azure DevOps Server webhook password")

    # Gerrit-specific
    gerrit_user: Optional[str] = Field(default=None, description="Gerrit user")
    patch_server_endpoint: Optional[str] = Field(default=None, description="Gerrit patch server endpoint")
    patch_server_token: Optional[str] = Field(default=None, description="Gerrit patch server token")


class GitProviderUpdate(SQLModel):
    """Model for updating an existing git provider."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    base_url: Optional[str] = Field(default=None, max_length=500)
    webhook_secret: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)
    is_default: Optional[bool] = Field(default=None)
    deployment_type: Optional[GitHubDeploymentType] = Field(default=None)
    auth_type: Optional[BitbucketAuthType] = Field(default=None)
    organization: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    app_id: Optional[str] = Field(default=None)
    private_key: Optional[str] = Field(default=None)
    basic_token: Optional[str] = Field(default=None)
    app_key: Optional[str] = Field(default=None)
    pat: Optional[str] = Field(default=None)
    webhook_username: Optional[str] = Field(default=None)
    webhook_password: Optional[str] = Field(default=None)
    gerrit_user: Optional[str] = Field(default=None)
    patch_server_endpoint: Optional[str] = Field(default=None)
    patch_server_token: Optional[str] = Field(default=None)


class GitProviderPublic(SQLModel):
    """Model for public API responses (excludes sensitive fields like tokens/keys)."""
    id: int
    type: GitProviderType
    name: str
    base_url: Optional[str]
    is_active: bool
    is_default: bool
    deployment_type: Optional[GitHubDeploymentType]
    auth_type: Optional[BitbucketAuthType]
    organization: Optional[str]
    # Indicate presence of credentials without exposing values
    has_access_token: bool = False
    has_app_credentials: bool = False
    has_webhook_secret: bool = False
    created_at: datetime
    updated_at: datetime


# =============================================================================
# LLM Provider models
# =============================================================================

class LLMProviderBase(SQLModel):
    """Base model for LLM provider with shared fields."""
    type: LLMProviderType = Field(description="LLM provider type")
    name: str = Field(min_length=1, max_length=255, description="Display name for this configuration")
    is_active: bool = Field(default=True, description="Whether the provider is active")
    is_default: bool = Field(default=False, description="Whether this is the default LLM provider")

    # Common fields across most providers
    api_key: Optional[str] = Field(default=None, max_length=500, description="API key for authentication")
    api_base: Optional[str] = Field(default=None, max_length=500, description="Base URL for API calls")

    # OpenAI-specific fields
    organization: Optional[str] = Field(default=None, max_length=255, description="OpenAI organization ID")
    api_type: Optional[OpenAIApiType] = Field(default=None, description="API type (openai or azure)")
    api_version: Optional[str] = Field(default=None, max_length=50, description="Azure OpenAI API version")
    deployment_id: Optional[str] = Field(default=None, max_length=255, description="Azure OpenAI deployment ID")
    fallback_deployments: Optional[str] = Field(default=None, description="Comma-separated fallback deployment IDs")

    # Azure AD-specific fields
    client_id: Optional[str] = Field(default=None, max_length=255, description="Azure AD client ID")
    client_secret: Optional[str] = Field(default=None, max_length=500, description="Azure AD client secret")
    tenant_id: Optional[str] = Field(default=None, max_length=255, description="Azure AD tenant ID")

    # VertexAI-specific fields
    vertex_project: Optional[str] = Field(default=None, max_length=255, description="Google Cloud project name")
    vertex_location: Optional[str] = Field(default=None, max_length=100, description="Google Cloud location")

    # AWS-specific fields
    aws_access_key_id: Optional[str] = Field(default=None, max_length=255, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, max_length=500, description="AWS secret access key")
    aws_region_name: Optional[str] = Field(default=None, max_length=100, description="AWS region name")

    # LiteLLM-specific fields
    extra_body: Optional[str] = Field(default=None, description="Extra body parameters as JSON string")
    model_id: Optional[str] = Field(default=None, max_length=255, description="Custom model/inference profile ID")


class LLMProvider(LLMProviderBase, table=True):
    """LLM provider database model for storing AI service credentials."""
    __tablename__ = "llm_providers"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LLMProviderCreate(LLMProviderBase):
    """Model for creating a new LLM provider."""
    pass


class LLMProviderUpdate(SQLModel):
    """Model for updating an existing LLM provider."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = Field(default=None)
    is_default: Optional[bool] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    api_base: Optional[str] = Field(default=None)
    organization: Optional[str] = Field(default=None)
    api_type: Optional[OpenAIApiType] = Field(default=None)
    api_version: Optional[str] = Field(default=None)
    deployment_id: Optional[str] = Field(default=None)
    fallback_deployments: Optional[str] = Field(default=None)
    client_id: Optional[str] = Field(default=None)
    client_secret: Optional[str] = Field(default=None)
    tenant_id: Optional[str] = Field(default=None)
    vertex_project: Optional[str] = Field(default=None)
    vertex_location: Optional[str] = Field(default=None)
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_region_name: Optional[str] = Field(default=None)
    extra_body: Optional[str] = Field(default=None)
    model_id: Optional[str] = Field(default=None)


class LLMProviderPublic(SQLModel):
    """Model for public API responses (excludes sensitive fields like API keys)."""
    id: int
    type: LLMProviderType
    name: str
    is_active: bool
    is_default: bool
    api_base: Optional[str]
    organization: Optional[str]
    api_type: Optional[OpenAIApiType]
    api_version: Optional[str]
    deployment_id: Optional[str]
    vertex_project: Optional[str]
    vertex_location: Optional[str]
    aws_region_name: Optional[str]
    model_id: Optional[str]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Vector Database Provider models
# =============================================================================

class VectorDBProviderBase(SQLModel):
    """Base model for vector database provider."""
    type: VectorDBType = Field(description="Vector database type")
    name: str = Field(min_length=1, max_length=255, description="Display name")
    is_active: bool = Field(default=True, description="Whether the provider is active")
    is_default: bool = Field(default=False, description="Whether this is the default vector DB")

    # Common fields
    api_key: Optional[str] = Field(default=None, max_length=500, description="API key")
    url: Optional[str] = Field(default=None, max_length=500, description="Service URL")

    # Pinecone-specific
    environment: Optional[str] = Field(default=None, max_length=100, description="Pinecone environment")

    # LanceDB-specific
    uri: Optional[str] = Field(default=None, max_length=500, description="LanceDB URI path")


class VectorDBProvider(VectorDBProviderBase, table=True):
    """Vector database provider for similar issues feature."""
    __tablename__ = "vector_db_providers"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VectorDBProviderCreate(VectorDBProviderBase):
    """Model for creating a new vector DB provider."""
    pass


class VectorDBProviderUpdate(SQLModel):
    """Model for updating an existing vector DB provider."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = Field(default=None)
    is_default: Optional[bool] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    environment: Optional[str] = Field(default=None)
    uri: Optional[str] = Field(default=None)


class VectorDBProviderPublic(SQLModel):
    """Model for public API responses (excludes sensitive fields)."""
    id: int
    type: VectorDBType
    name: str
    is_active: bool
    is_default: bool
    url: Optional[str]
    environment: Optional[str]
    uri: Optional[str]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# PR-Agent Configuration models
# =============================================================================

class PRAgentConfig(SQLModel, table=True):
    """
    PR-Agent configuration model for storing settings from configuration.toml.

    Uses JSON columns for flexible storage of configuration sections.
    Each section (pr_reviewer, pr_description, etc.) is stored as a JSON object.
    """
    __tablename__ = "pr_agent_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=255, description="Configuration profile name")
    is_active: bool = Field(default=True, description="Whether this config is active")
    is_default: bool = Field(default=False, description="Whether this is the default config")

    # [config] section - General settings
    model: str = Field(default="gpt-4", max_length=255, description="Primary model to use")
    fallback_models: Optional[str] = Field(default=None, description="Comma-separated fallback models")
    model_reasoning: Optional[str] = Field(default=None, max_length=255, description="Dedicated reasoning model")
    model_weak: Optional[str] = Field(default=None, max_length=255, description="Weaker model for easier tasks")
    git_provider: str = Field(default="github", max_length=50, description="Default git provider")
    publish_output: bool = Field(default=True, description="Publish output to PR")
    publish_output_progress: bool = Field(default=True, description="Show progress updates")
    verbosity_level: int = Field(default=0, ge=0, le=2, description="Verbosity level (0-2)")
    use_extra_bad_extensions: bool = Field(default=False)
    log_level: str = Field(default="DEBUG", max_length=20)
    ai_timeout: int = Field(default=120, description="AI request timeout in seconds")
    custom_reasoning_model: bool = Field(default=False)
    response_language: str = Field(default="en-US", max_length=10)

    # Token limits
    max_description_tokens: int = Field(default=500)
    max_commits_tokens: int = Field(default=500)
    max_model_tokens: int = Field(default=32000)
    custom_model_max_tokens: int = Field(default=32000)

    # Model parameters
    seed: int = Field(default=-1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    reasoning_effort: str = Field(default="medium", max_length=20)

    # Claude extended thinking
    enable_claude_extended_thinking: bool = Field(default=False)
    extended_thinking_budget_tokens: int = Field(default=2048)
    extended_thinking_max_output_tokens: int = Field(default=4096)

    # Automation master switch. When True, PR-Agent does not run any
    # automatic tools on PR/push events across any git provider. Manual
    # slash-command triggers still work.
    disable_auto_feedback: bool = Field(default=False)

    # Tool-specific configurations stored as JSON
    pr_reviewer_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_description_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_questions_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_code_suggestions_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_custom_prompt_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_add_docs_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_update_changelog_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_analyze_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_test_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_improve_component_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_help_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    pr_help_docs_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Provider-specific command configs stored as JSON
    github_app_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    gitlab_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    gitea_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    bitbucket_app_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    bitbucket_server_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    azure_devops_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Other settings as JSON
    best_practices_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    auto_best_practices_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    similar_issue_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    litellm_config: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Ignore patterns as JSON arrays
    ignore_pr_title: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    ignore_pr_target_branches: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    ignore_pr_source_branches: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    ignore_pr_labels: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    ignore_pr_authors: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    ignore_repositories: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PRAgentConfigCreate(SQLModel):
    """Model for creating a new PR-Agent configuration."""
    name: str = Field(min_length=1, max_length=255)
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)

    # General settings
    model: str = Field(default="gpt-4")
    fallback_models: Optional[str] = Field(default=None)
    model_reasoning: Optional[str] = Field(default=None)
    model_weak: Optional[str] = Field(default=None)
    git_provider: str = Field(default="github")
    publish_output: bool = Field(default=True)
    publish_output_progress: bool = Field(default=True)
    verbosity_level: int = Field(default=0)
    use_extra_bad_extensions: bool = Field(default=False)
    log_level: str = Field(default="DEBUG")
    ai_timeout: int = Field(default=120)
    custom_reasoning_model: bool = Field(default=False)
    response_language: str = Field(default="en-US")

    # Token limits
    max_description_tokens: int = Field(default=500)
    max_commits_tokens: int = Field(default=500)
    max_model_tokens: int = Field(default=32000)
    custom_model_max_tokens: int = Field(default=32000)

    # Model parameters
    seed: int = Field(default=-1)
    temperature: float = Field(default=0.2)
    reasoning_effort: str = Field(default="medium")

    # Claude extended thinking
    enable_claude_extended_thinking: bool = Field(default=False)
    extended_thinking_budget_tokens: int = Field(default=2048)
    extended_thinking_max_output_tokens: int = Field(default=4096)

    # Automation master switch (see PRAgentConfig).
    disable_auto_feedback: bool = Field(default=False)

    # Tool-specific configurations
    pr_reviewer_config: Optional[dict[str, Any]] = Field(default=None)
    pr_description_config: Optional[dict[str, Any]] = Field(default=None)
    pr_questions_config: Optional[dict[str, Any]] = Field(default=None)
    pr_code_suggestions_config: Optional[dict[str, Any]] = Field(default=None)
    pr_custom_prompt_config: Optional[dict[str, Any]] = Field(default=None)
    pr_add_docs_config: Optional[dict[str, Any]] = Field(default=None)
    pr_update_changelog_config: Optional[dict[str, Any]] = Field(default=None)
    pr_analyze_config: Optional[dict[str, Any]] = Field(default=None)
    pr_test_config: Optional[dict[str, Any]] = Field(default=None)
    pr_improve_component_config: Optional[dict[str, Any]] = Field(default=None)
    pr_help_config: Optional[dict[str, Any]] = Field(default=None)
    pr_help_docs_config: Optional[dict[str, Any]] = Field(default=None)

    # Provider configs
    github_app_config: Optional[dict[str, Any]] = Field(default=None)
    gitlab_config: Optional[dict[str, Any]] = Field(default=None)
    gitea_config: Optional[dict[str, Any]] = Field(default=None)
    bitbucket_app_config: Optional[dict[str, Any]] = Field(default=None)
    bitbucket_server_config: Optional[dict[str, Any]] = Field(default=None)
    azure_devops_config: Optional[dict[str, Any]] = Field(default=None)

    # Other configs
    best_practices_config: Optional[dict[str, Any]] = Field(default=None)
    auto_best_practices_config: Optional[dict[str, Any]] = Field(default=None)
    similar_issue_config: Optional[dict[str, Any]] = Field(default=None)
    litellm_config: Optional[dict[str, Any]] = Field(default=None)

    # Ignore patterns
    ignore_pr_title: Optional[list[str]] = Field(default=None)
    ignore_pr_target_branches: Optional[list[str]] = Field(default=None)
    ignore_pr_source_branches: Optional[list[str]] = Field(default=None)
    ignore_pr_labels: Optional[list[str]] = Field(default=None)
    ignore_pr_authors: Optional[list[str]] = Field(default=None)
    ignore_repositories: Optional[list[str]] = Field(default=None)


class PRAgentConfigUpdate(SQLModel):
    """Model for updating an existing PR-Agent configuration."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = Field(default=None)
    is_default: Optional[bool] = Field(default=None)
    model: Optional[str] = Field(default=None)
    fallback_models: Optional[str] = Field(default=None)
    model_reasoning: Optional[str] = Field(default=None)
    model_weak: Optional[str] = Field(default=None)
    git_provider: Optional[str] = Field(default=None)
    publish_output: Optional[bool] = Field(default=None)
    publish_output_progress: Optional[bool] = Field(default=None)
    verbosity_level: Optional[int] = Field(default=None)
    use_extra_bad_extensions: Optional[bool] = Field(default=None)
    log_level: Optional[str] = Field(default=None)
    ai_timeout: Optional[int] = Field(default=None)
    custom_reasoning_model: Optional[bool] = Field(default=None)
    response_language: Optional[str] = Field(default=None)
    max_description_tokens: Optional[int] = Field(default=None)
    max_commits_tokens: Optional[int] = Field(default=None)
    max_model_tokens: Optional[int] = Field(default=None)
    custom_model_max_tokens: Optional[int] = Field(default=None)
    seed: Optional[int] = Field(default=None)
    temperature: Optional[float] = Field(default=None)
    reasoning_effort: Optional[str] = Field(default=None)
    enable_claude_extended_thinking: Optional[bool] = Field(default=None)
    extended_thinking_budget_tokens: Optional[int] = Field(default=None)
    extended_thinking_max_output_tokens: Optional[int] = Field(default=None)
    disable_auto_feedback: Optional[bool] = Field(default=None)
    pr_reviewer_config: Optional[dict[str, Any]] = Field(default=None)
    pr_description_config: Optional[dict[str, Any]] = Field(default=None)
    pr_questions_config: Optional[dict[str, Any]] = Field(default=None)
    pr_code_suggestions_config: Optional[dict[str, Any]] = Field(default=None)
    pr_custom_prompt_config: Optional[dict[str, Any]] = Field(default=None)
    pr_add_docs_config: Optional[dict[str, Any]] = Field(default=None)
    pr_update_changelog_config: Optional[dict[str, Any]] = Field(default=None)
    pr_analyze_config: Optional[dict[str, Any]] = Field(default=None)
    pr_test_config: Optional[dict[str, Any]] = Field(default=None)
    pr_improve_component_config: Optional[dict[str, Any]] = Field(default=None)
    pr_help_config: Optional[dict[str, Any]] = Field(default=None)
    pr_help_docs_config: Optional[dict[str, Any]] = Field(default=None)
    github_app_config: Optional[dict[str, Any]] = Field(default=None)
    gitlab_config: Optional[dict[str, Any]] = Field(default=None)
    gitea_config: Optional[dict[str, Any]] = Field(default=None)
    bitbucket_app_config: Optional[dict[str, Any]] = Field(default=None)
    bitbucket_server_config: Optional[dict[str, Any]] = Field(default=None)
    azure_devops_config: Optional[dict[str, Any]] = Field(default=None)
    best_practices_config: Optional[dict[str, Any]] = Field(default=None)
    auto_best_practices_config: Optional[dict[str, Any]] = Field(default=None)
    similar_issue_config: Optional[dict[str, Any]] = Field(default=None)
    litellm_config: Optional[dict[str, Any]] = Field(default=None)
    ignore_pr_title: Optional[list[str]] = Field(default=None)
    ignore_pr_target_branches: Optional[list[str]] = Field(default=None)
    ignore_pr_source_branches: Optional[list[str]] = Field(default=None)
    ignore_pr_labels: Optional[list[str]] = Field(default=None)
    ignore_pr_authors: Optional[list[str]] = Field(default=None)
    ignore_repositories: Optional[list[str]] = Field(default=None)


class PRAgentConfigPublic(SQLModel):
    """Model for public API responses."""
    id: int
    name: str
    is_active: bool
    is_default: bool
    model: str
    fallback_models: Optional[str]
    model_reasoning: Optional[str]
    model_weak: Optional[str]
    git_provider: str
    publish_output: bool
    publish_output_progress: bool
    verbosity_level: int
    log_level: str
    ai_timeout: int
    response_language: str
    max_description_tokens: int
    max_commits_tokens: int
    max_model_tokens: int
    temperature: float
    reasoning_effort: str
    enable_claude_extended_thinking: bool
    disable_auto_feedback: bool
    pr_reviewer_config: Optional[dict[str, Any]]
    pr_description_config: Optional[dict[str, Any]]
    pr_questions_config: Optional[dict[str, Any]]
    pr_code_suggestions_config: Optional[dict[str, Any]]
    github_app_config: Optional[dict[str, Any]]
    gitlab_config: Optional[dict[str, Any]]
    ignore_pr_title: Optional[list[str]]
    ignore_pr_target_branches: Optional[list[str]]
    ignore_pr_source_branches: Optional[list[str]]
    ignore_pr_labels: Optional[list[str]]
    ignore_pr_authors: Optional[list[str]]
    ignore_repositories: Optional[list[str]]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Webhook registration models
#
# One row per (git_provider, repo) pairing. Stores the webhook URL + secret +
# event list we want on the remote git host, plus a cached `external_id` and
# last-delivery status for quick reference in the Dashboard.
# =============================================================================


class WebhookRegistrationStatus(str, Enum):
    """Lifecycle state for a webhook registration."""
    draft = "draft"              # stored locally, not registered with provider
    registered = "registered"    # provider confirmed creation
    failed = "failed"            # last register/update attempt errored
    deleted = "deleted"          # removed from provider (kept locally for audit)


class WebhookRegistration(SQLModel, table=True):
    """Webhook registered on a remote git provider for a specific repository."""

    __tablename__ = "webhook_registrations"

    id: Optional[int] = Field(default=None, primary_key=True)

    # FK to git_providers.id; a webhook always belongs to one credential set.
    git_provider_id: int = Field(
        foreign_key="git_providers.id",
        index=True,
        description="Git provider credential used to manage this webhook.",
    )

    repo: str = Field(min_length=1, max_length=500, index=True)
    target_url: str = Field(min_length=1, max_length=1000)

    # Event list stored as JSON so we don't need a join table for a handful of strings.
    events: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))

    active: bool = Field(default=True)
    content_type: str = Field(default="json", max_length=20)
    insecure_ssl: bool = Field(default=False)

    # Secret sent in X-Hub-Signature / X-Gitlab-Token headers. Stored in plaintext
    # here for simplicity; mirror your credentials-store encryption strategy.
    secret: Optional[str] = Field(default=None, max_length=500)

    # Identifier returned by the provider after registration (GitHub: numeric hook id,
    # GitLab: integer project hook id). Null while status == draft.
    external_id: Optional[str] = Field(default=None, max_length=255, index=True)

    status: WebhookRegistrationStatus = Field(
        default=WebhookRegistrationStatus.draft,
        description="Local bookkeeping state; updated by the register/unregister endpoints.",
    )

    # Last-delivery bookkeeping fields for quick dashboard display.
    last_delivery_at: Optional[datetime] = Field(default=None)
    last_status_code: Optional[int] = Field(default=None)
    last_error: Optional[str] = Field(default=None, max_length=2000)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookRegistrationCreate(SQLModel):
    """Input for creating a new webhook registration row (not yet registered)."""
    git_provider_id: int
    repo: str = Field(min_length=1, max_length=500)
    target_url: str = Field(min_length=1, max_length=1000)
    events: Optional[list[str]] = Field(default=None)
    active: bool = True
    content_type: str = Field(default="json", max_length=20)
    insecure_ssl: bool = False
    secret: Optional[str] = Field(
        default=None,
        description="Optional secret. If omitted, callers may generate one server-side.",
    )


class WebhookRegistrationUpdate(SQLModel):
    """Partial update payload. Only provided fields are changed."""
    repo: Optional[str] = Field(default=None, min_length=1, max_length=500)
    target_url: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    events: Optional[list[str]] = Field(default=None)
    active: Optional[bool] = Field(default=None)
    content_type: Optional[str] = Field(default=None, max_length=20)
    insecure_ssl: Optional[bool] = Field(default=None)
    secret: Optional[str] = Field(default=None)


class WebhookRegistrationPublic(SQLModel):
    """Public-safe API response (excludes the raw secret)."""
    id: int
    git_provider_id: int
    repo: str
    target_url: str
    events: list[str]
    active: bool
    content_type: str
    insecure_ssl: bool
    status: WebhookRegistrationStatus
    external_id: Optional[str]
    has_secret: bool
    last_delivery_at: Optional[datetime]
    last_status_code: Optional[int]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class WebhookDelivery(SQLModel):
    """Transient delivery record returned by provider APIs (not persisted)."""
    id: str
    delivered_at: Optional[datetime] = None
    status: Optional[str] = None
    status_code: Optional[int] = None
    event: Optional[str] = None
    action: Optional[str] = None
    duration_ms: Optional[float] = None
    redelivery: bool = False
    url: Optional[str] = None
