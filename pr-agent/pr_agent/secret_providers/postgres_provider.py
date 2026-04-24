"""
PostgreSQL Credential Provider for PR-Agent.

Reads git provider and LLM provider credentials from PostgreSQL database (stored via Dashboard).
Falls back to .secrets.toml if no matching provider is found in the database.
"""

import os
import threading
import time
from typing import Any, Optional

# LLM provider type to settings key mapping
LLM_PROVIDER_SETTINGS_MAP = {
    "openai": {
        "key_setting": "OPENAI.KEY",
        "api_base_setting": "OPENAI.API_BASE",
        "org_setting": "OPENAI.ORG",
    },
    "anthropic": {
        "key_setting": "ANTHROPIC.KEY",
    },
    "cohere": {
        "key_setting": "COHERE.KEY",
    },
    "replicate": {
        "key_setting": "REPLICATE.KEY",
    },
    "groq": {
        "key_setting": "GROQ.KEY",
    },
    "xai": {
        "key_setting": "XAI.KEY",
    },
    "huggingface": {
        "key_setting": "HUGGINGFACE.KEY",
        "api_base_setting": "HUGGINGFACE.API_BASE",
    },
    "ollama": {
        "key_setting": "OLLAMA.API_KEY",
        "api_base_setting": "OLLAMA.API_BASE",
    },
    "vertexai": {
        "project_setting": "VERTEXAI.VERTEX_PROJECT",
        "location_setting": "VERTEXAI.VERTEX_LOCATION",
    },
    "google_ai_studio": {
        "key_setting": "GOOGLE_AI_STUDIO.GEMINI_API_KEY",
    },
    "deepseek": {
        "key_setting": "DEEPSEEK.KEY",
    },
    "deepinfra": {
        "key_setting": "DEEPINFRA.KEY",
    },
    "azure_openai": {
        "key_setting": "OPENAI.KEY",
        "api_base_setting": "OPENAI.API_BASE",
        "api_type_setting": "OPENAI.API_TYPE",
        "api_version_setting": "OPENAI.API_VERSION",
        "deployment_id_setting": "OPENAI.DEPLOYMENT_ID",
    },
    "azure_ad": {
        "client_id_setting": "AZURE_AD.CLIENT_ID",
        "client_secret_setting": "AZURE_AD.CLIENT_SECRET",
        "tenant_id_setting": "AZURE_AD.TENANT_ID",
        "api_base_setting": "AZURE_AD.API_BASE",
    },
    "openrouter": {
        "key_setting": "OPENROUTER.KEY",
        "api_base_setting": "OPENROUTER.API_BASE",
    },
    "aws_bedrock": {
        "access_key_setting": "AWS.AWS_ACCESS_KEY_ID",
        "secret_key_setting": "AWS.AWS_SECRET_ACCESS_KEY",
        "region_setting": "AWS.AWS_REGION_NAME",
    },
    "litellm": {
        "extra_body_setting": "LITELLM.EXTRA_BODY",
        "model_id_setting": "LITELLM.MODEL_ID",
    },
}


class PostgresCredentialProvider:
    """
    Provides credentials from PostgreSQL database.

    Usage:
        provider = PostgresCredentialProvider()
        creds = provider.get_credentials("github")
        # Returns: {"token": "ghp_xxx", "deployment_type": "user", ...}
    """

    def __init__(self):
        self._session = None
        self._engine = None
        self._initialized = False

    def _init_db(self):
        """Lazy initialization of database connection."""
        if self._initialized:
            return

        try:
            from sqlmodel import create_engine

            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                self._initialized = False
                return

            self._engine = create_engine(database_url)
            self._initialized = True
        except Exception:
            self._initialized = False

    def get_credentials(self, provider_type: str, repo_full_name: Optional[str] = None) -> Optional[dict]:
        """
        Get credentials for a git provider type.

        Args:
            provider_type: One of "github", "gitlab", "bitbucket", etc.
            repo_full_name: Optional repo name (for future per-repo credentials)

        Returns:
            Dictionary with credentials, or None if not found.
        """
        self._init_db()

        if not self._initialized or not self._engine:
            return None

        try:
            from sqlmodel import Session, select
            from pr_agent.db.models import GitProvider

            with Session(self._engine) as session:
                # Find first active provider of this type
                statement = select(GitProvider).where(
                    GitProvider.type == provider_type,
                    GitProvider.is_active == True
                ).limit(1)

                provider = session.exec(statement).first()

                if not provider:
                    return None

                # Build credentials dict based on provider type
                creds = {
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                }

                if provider_type == "github":
                    if provider.deployment_type and provider.deployment_type.value == "app":
                        creds["deployment_type"] = "app"
                        creds["app_id"] = provider.app_id
                        creds["private_key"] = provider.private_key
                    else:
                        creds["deployment_type"] = "user"
                        creds["user_token"] = provider.access_token

                    if provider.webhook_secret:
                        creds["webhook_secret"] = provider.webhook_secret

                elif provider_type == "gitlab":
                    creds["personal_access_token"] = provider.access_token
                    if provider.webhook_secret:
                        creds["shared_secret"] = provider.webhook_secret
                    if provider.base_url:
                        creds["url"] = provider.base_url

                elif provider_type == "bitbucket":
                    creds["bearer_token"] = provider.access_token
                    if provider.webhook_secret:
                        creds["webhook_secret"] = provider.webhook_secret

                elif provider_type == "azure_devops":
                    creds["pat"] = provider.access_token

                elif provider_type == "gitea":
                    creds["personal_access_token"] = provider.access_token
                    if provider.webhook_secret:
                        creds["webhook_secret"] = provider.webhook_secret

                else:
                    # Generic fallback
                    creds["token"] = provider.access_token

                # Add base_url if set (for self-hosted)
                if provider.base_url:
                    creds["base_url"] = provider.base_url

                return creds

        except Exception:
            return None

    def get_llm_credentials(self, provider_type: Optional[str] = None) -> Optional[dict]:
        """
        Get credentials for an LLM provider.

        Args:
            provider_type: Optional specific type. If None, returns the default or first active provider.

        Returns:
            Dictionary with credentials, or None if not found.
        """
        self._init_db()

        if not self._initialized or not self._engine:
            return None

        try:
            from sqlmodel import Session, select
            from pr_agent.db.models import LLMProvider

            with Session(self._engine) as session:
                if provider_type:
                    # Find specific provider type
                    statement = select(LLMProvider).where(
                        LLMProvider.type == provider_type,
                        LLMProvider.is_active == True
                    ).limit(1)
                else:
                    # Find default provider first, then any active provider
                    statement = select(LLMProvider).where(
                        LLMProvider.is_default == True,
                        LLMProvider.is_active == True
                    ).limit(1)

                provider = session.exec(statement).first()

                # If no default, get first active
                if not provider and not provider_type:
                    statement = select(LLMProvider).where(
                        LLMProvider.is_active == True
                    ).limit(1)
                    provider = session.exec(statement).first()

                if not provider:
                    return None

                # Build credentials dict
                creds = {
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "provider_type": provider.type.value if hasattr(provider.type, 'value') else str(provider.type),
                }

                # Common fields
                if provider.api_key:
                    creds["api_key"] = provider.api_key
                if provider.api_base:
                    creds["api_base"] = provider.api_base
                if provider.organization:
                    creds["organization"] = provider.organization

                # OpenAI/Azure specific
                if provider.api_type:
                    creds["api_type"] = provider.api_type.value if hasattr(provider.api_type, 'value') else str(provider.api_type)
                if provider.api_version:
                    creds["api_version"] = provider.api_version
                if provider.deployment_id:
                    creds["deployment_id"] = provider.deployment_id
                if provider.fallback_deployments:
                    creds["fallback_deployments"] = provider.fallback_deployments

                # Azure AD specific
                if provider.client_id:
                    creds["client_id"] = provider.client_id
                if provider.client_secret:
                    creds["client_secret"] = provider.client_secret
                if provider.tenant_id:
                    creds["tenant_id"] = provider.tenant_id

                # VertexAI specific
                if provider.vertex_project:
                    creds["vertex_project"] = provider.vertex_project
                if provider.vertex_location:
                    creds["vertex_location"] = provider.vertex_location

                # AWS specific
                if provider.aws_access_key_id:
                    creds["aws_access_key_id"] = provider.aws_access_key_id
                if provider.aws_secret_access_key:
                    creds["aws_secret_access_key"] = provider.aws_secret_access_key
                if provider.aws_region_name:
                    creds["aws_region_name"] = provider.aws_region_name

                # LiteLLM specific
                if provider.extra_body:
                    creds["extra_body"] = provider.extra_body
                if provider.model_id:
                    creds["model_id"] = provider.model_id

                return creds

        except Exception:
            return None

    def get_all_llm_credentials(self) -> list[dict]:
        """
        Get all active LLM provider credentials.

        Returns:
            List of credential dictionaries for all active providers.
        """
        self._init_db()

        if not self._initialized or not self._engine:
            return []

        try:
            from sqlmodel import Session, select
            from pr_agent.db.models import LLMProvider

            with Session(self._engine) as session:
                statement = select(LLMProvider).where(LLMProvider.is_active == True)
                providers = session.exec(statement).all()

                results = []
                for provider in providers:
                    creds = {
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "provider_type": provider.type.value if hasattr(provider.type, 'value') else str(provider.type),
                        "is_default": provider.is_default,
                    }

                    if provider.api_key:
                        creds["api_key"] = provider.api_key
                    if provider.api_base:
                        creds["api_base"] = provider.api_base
                    if provider.organization:
                        creds["organization"] = provider.organization
                    if provider.api_type:
                        creds["api_type"] = provider.api_type.value if hasattr(provider.api_type, 'value') else str(provider.api_type)
                    if provider.api_version:
                        creds["api_version"] = provider.api_version
                    if provider.deployment_id:
                        creds["deployment_id"] = provider.deployment_id
                    if provider.client_id:
                        creds["client_id"] = provider.client_id
                    if provider.client_secret:
                        creds["client_secret"] = provider.client_secret
                    if provider.tenant_id:
                        creds["tenant_id"] = provider.tenant_id
                    if provider.vertex_project:
                        creds["vertex_project"] = provider.vertex_project
                    if provider.vertex_location:
                        creds["vertex_location"] = provider.vertex_location
                    if provider.aws_access_key_id:
                        creds["aws_access_key_id"] = provider.aws_access_key_id
                    if provider.aws_secret_access_key:
                        creds["aws_secret_access_key"] = provider.aws_secret_access_key
                    if provider.aws_region_name:
                        creds["aws_region_name"] = provider.aws_region_name
                    if provider.extra_body:
                        creds["extra_body"] = provider.extra_body
                    if provider.model_id:
                        creds["model_id"] = provider.model_id

                    results.append(creds)

                return results

        except Exception:
            return []


# Singleton instance
_postgres_provider: Optional[PostgresCredentialProvider] = None


def get_postgres_credential_provider() -> PostgresCredentialProvider:
    """Get or create the singleton PostgresCredentialProvider."""
    global _postgres_provider
    if _postgres_provider is None:
        _postgres_provider = PostgresCredentialProvider()
    return _postgres_provider


def apply_postgres_credentials_to_config():
    """
    Load credentials from PostgreSQL and apply to PR-Agent configuration.

    This should be called early in initialization, before git providers are created.
    Only applies if DATABASE_URL environment variable is set.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return

    try:
        from pr_agent.config_loader import get_settings

        provider = get_postgres_credential_provider()

        # Try to load GitHub credentials
        github_creds = provider.get_credentials("github")
        if github_creds:
            if github_creds.get("deployment_type") == "app":
                get_settings().set("GITHUB.DEPLOYMENT_TYPE", "app")
                if github_creds.get("app_id"):
                    get_settings().set("GITHUB.APP_ID", github_creds["app_id"])
                if github_creds.get("private_key"):
                    get_settings().set("GITHUB.PRIVATE_KEY", github_creds["private_key"])
            else:
                get_settings().set("GITHUB.DEPLOYMENT_TYPE", "user")
                if github_creds.get("user_token"):
                    get_settings().set("GITHUB.USER_TOKEN", github_creds["user_token"])

            if github_creds.get("webhook_secret"):
                get_settings().set("GITHUB.WEBHOOK_SECRET", github_creds["webhook_secret"])
            if github_creds.get("base_url"):
                get_settings().set("GITHUB.BASE_URL", github_creds["base_url"])

        # Try to load GitLab credentials
        gitlab_creds = provider.get_credentials("gitlab")
        if gitlab_creds:
            if gitlab_creds.get("personal_access_token"):
                get_settings().set("GITLAB.PERSONAL_ACCESS_TOKEN", gitlab_creds["personal_access_token"])
            if gitlab_creds.get("shared_secret"):
                get_settings().set("GITLAB.SHARED_SECRET", gitlab_creds["shared_secret"])
            if gitlab_creds.get("url"):
                get_settings().set("GITLAB.URL", gitlab_creds["url"])

        # Try to load Bitbucket credentials
        bitbucket_creds = provider.get_credentials("bitbucket")
        if bitbucket_creds:
            if bitbucket_creds.get("bearer_token"):
                get_settings().set("BITBUCKET.BEARER_TOKEN", bitbucket_creds["bearer_token"])
            if bitbucket_creds.get("webhook_secret"):
                get_settings().set("BITBUCKET.WEBHOOK_SECRET", bitbucket_creds["webhook_secret"])

        # Try to load Azure DevOps credentials
        azure_creds = provider.get_credentials("azure_devops")
        if azure_creds:
            if azure_creds.get("pat"):
                get_settings().set("AZURE_DEVOPS.PAT", azure_creds["pat"])

        # Try to load Gitea credentials
        gitea_creds = provider.get_credentials("gitea")
        if gitea_creds:
            if gitea_creds.get("personal_access_token"):
                get_settings().set("GITEA.PERSONAL_ACCESS_TOKEN", gitea_creds["personal_access_token"])
            if gitea_creds.get("webhook_secret"):
                get_settings().set("GITEA.WEBHOOK_SECRET", gitea_creds["webhook_secret"])

        # =================================================================
        # Load LLM provider credentials
        # =================================================================
        llm_creds = provider.get_llm_credentials()
        if llm_creds:
            provider_type = llm_creds.get("provider_type", "")

            # Set the model from database (model_id field)
            # For litellm, the model needs provider prefix (e.g., "openai/model-name")
            if llm_creds.get("model_id"):
                model_id = llm_creds["model_id"]
                # Known provider prefixes that litellm recognizes
                known_prefixes = (
                    "openai/", "anthropic/", "azure/", "huggingface/", "ollama/",
                    "vertexai/", "vertex_ai/", "gemini/", "bedrock/", "cohere/",
                    "replicate/", "groq/", "xai/", "deepseek/", "deepinfra/",
                    "mistral/", "codestral/", "watsonx/"
                )
                # Add provider prefix if model doesn't already have a known prefix
                if provider_type and not model_id.startswith(known_prefixes):
                    model_id = f"{provider_type}/{model_id}"
                get_settings().set("CONFIG.MODEL", model_id)

            # Apply credentials based on provider type
            if provider_type == "openai":
                if llm_creds.get("api_key"):
                    get_settings().set("OPENAI.KEY", llm_creds["api_key"])
                if llm_creds.get("organization"):
                    get_settings().set("OPENAI.ORG", llm_creds["organization"])
                if llm_creds.get("api_base"):
                    get_settings().set("OPENAI.API_BASE", llm_creds["api_base"])

            elif provider_type == "anthropic":
                if llm_creds.get("api_key"):
                    get_settings().set("ANTHROPIC.KEY", llm_creds["api_key"])

            elif provider_type == "cohere":
                if llm_creds.get("api_key"):
                    get_settings().set("COHERE.KEY", llm_creds["api_key"])

            elif provider_type == "replicate":
                if llm_creds.get("api_key"):
                    get_settings().set("REPLICATE.KEY", llm_creds["api_key"])

            elif provider_type == "groq":
                if llm_creds.get("api_key"):
                    get_settings().set("GROQ.KEY", llm_creds["api_key"])

            elif provider_type == "xai":
                if llm_creds.get("api_key"):
                    get_settings().set("XAI.KEY", llm_creds["api_key"])

            elif provider_type == "huggingface":
                if llm_creds.get("api_key"):
                    get_settings().set("HUGGINGFACE.KEY", llm_creds["api_key"])
                if llm_creds.get("api_base"):
                    get_settings().set("HUGGINGFACE.API_BASE", llm_creds["api_base"])

            elif provider_type == "ollama":
                if llm_creds.get("api_key"):
                    get_settings().set("OLLAMA.API_KEY", llm_creds["api_key"])
                if llm_creds.get("api_base"):
                    get_settings().set("OLLAMA.API_BASE", llm_creds["api_base"])

            elif provider_type == "vertexai":
                if llm_creds.get("vertex_project"):
                    get_settings().set("VERTEXAI.VERTEX_PROJECT", llm_creds["vertex_project"])
                if llm_creds.get("vertex_location"):
                    get_settings().set("VERTEXAI.VERTEX_LOCATION", llm_creds["vertex_location"])

            elif provider_type == "google_ai_studio":
                if llm_creds.get("api_key"):
                    get_settings().set("GOOGLE_AI_STUDIO.GEMINI_API_KEY", llm_creds["api_key"])

            elif provider_type == "deepseek":
                if llm_creds.get("api_key"):
                    get_settings().set("DEEPSEEK.KEY", llm_creds["api_key"])

            elif provider_type == "deepinfra":
                if llm_creds.get("api_key"):
                    get_settings().set("DEEPINFRA.KEY", llm_creds["api_key"])

            elif provider_type == "azure_openai":
                if llm_creds.get("api_key"):
                    get_settings().set("OPENAI.KEY", llm_creds["api_key"])
                if llm_creds.get("api_base"):
                    get_settings().set("OPENAI.API_BASE", llm_creds["api_base"])
                get_settings().set("OPENAI.API_TYPE", "azure")
                if llm_creds.get("api_version"):
                    get_settings().set("OPENAI.API_VERSION", llm_creds["api_version"])
                if llm_creds.get("deployment_id"):
                    get_settings().set("OPENAI.DEPLOYMENT_ID", llm_creds["deployment_id"])

            elif provider_type == "azure_ad":
                if llm_creds.get("client_id"):
                    get_settings().set("AZURE_AD.CLIENT_ID", llm_creds["client_id"])
                if llm_creds.get("client_secret"):
                    get_settings().set("AZURE_AD.CLIENT_SECRET", llm_creds["client_secret"])
                if llm_creds.get("tenant_id"):
                    get_settings().set("AZURE_AD.TENANT_ID", llm_creds["tenant_id"])
                if llm_creds.get("api_base"):
                    get_settings().set("AZURE_AD.API_BASE", llm_creds["api_base"])

            elif provider_type == "openrouter":
                if llm_creds.get("api_key"):
                    get_settings().set("OPENROUTER.KEY", llm_creds["api_key"])
                if llm_creds.get("api_base"):
                    get_settings().set("OPENROUTER.API_BASE", llm_creds["api_base"])

            elif provider_type == "aws_bedrock":
                if llm_creds.get("aws_access_key_id"):
                    get_settings().set("AWS.AWS_ACCESS_KEY_ID", llm_creds["aws_access_key_id"])
                if llm_creds.get("aws_secret_access_key"):
                    get_settings().set("AWS.AWS_SECRET_ACCESS_KEY", llm_creds["aws_secret_access_key"])
                if llm_creds.get("aws_region_name"):
                    get_settings().set("AWS.AWS_REGION_NAME", llm_creds["aws_region_name"])

            elif provider_type == "litellm":
                if llm_creds.get("extra_body"):
                    get_settings().set("LITELLM.EXTRA_BODY", llm_creds["extra_body"])
                if llm_creds.get("model_id"):
                    get_settings().set("LITELLM.MODEL_ID", llm_creds["model_id"])

        # Apply automation config (per-provider pr_commands, push_commands, toggles).
        apply_automation_config_to_settings()

        # Apply knowledge-base config (/learn flag, extraction rules, retrieval tuning).
        apply_knowledge_base_config_to_settings()

    except Exception:
        # Silently fail - fall back to .secrets.toml
        pass


# =============================================================================
# Automation config (per-provider pr_commands / push_commands / toggles).
#
# These live in the JSON columns of the default PRAgentConfig row and are
# written from the Dashboard so administrators can change auto-review behavior
# without editing .pr_agent.toml or redeploying the webhook service.
# =============================================================================

# Mapping from PRAgentConfig JSON column to the Dynaconf section that
# pr-agent reads at runtime. Keep keys within each JSON in sync with the
# TOML keys in pr_agent/settings/configuration.toml.
_AUTOMATION_SECTION_MAP: dict[str, str] = {
    "github_app_config": "GITHUB_APP",
    "gitlab_config": "GITLAB",
    "bitbucket_app_config": "BITBUCKET_APP",
    "azure_devops_config": "AZURE_DEVOPS_SERVER",
    "gitea_config": "GITEA",
}

# Keys we allow the dashboard to push into Dynaconf. Additional keys stored in
# the JSON column are ignored here (they can be exposed later without changing
# the loader).
_AUTOMATION_ALLOWED_KEYS: tuple[str, ...] = (
    "pr_commands",
    "push_commands",
    "handle_push_trigger",
    "handle_pr_actions",
    "feedback_on_draft_pr",
)


def _fetch_automation_config() -> Optional[dict[str, Any]]:
    """Return the default PRAgentConfig row as a plain dict, or None.

    `disable_auto_feedback` is read from its dedicated column (added by
    Alembic revision `0002_add_disable_auto_feedback`). Each provider's JSON
    column is returned verbatim so the caller can push per-provider keys
    (pr_commands, push_commands, handle_push_trigger, …) into Dynaconf.
    """
    provider = get_postgres_credential_provider()
    provider._init_db()
    if not provider._initialized or not provider._engine:
        return None

    try:
        from sqlmodel import Session, select

        from pr_agent.db.models import PRAgentConfig

        with Session(provider._engine) as session:
            statement = select(PRAgentConfig).where(PRAgentConfig.is_default == True).limit(1)  # noqa: E712
            config = session.exec(statement).first()
            if not config:
                return None

            return {
                "id": config.id,
                "disable_auto_feedback": bool(config.disable_auto_feedback),
                "github_app_config": config.github_app_config or {},
                "gitlab_config": config.gitlab_config or {},
                "bitbucket_app_config": config.bitbucket_app_config or {},
                "azure_devops_config": config.azure_devops_config or {},
                "gitea_config": config.gitea_config or {},
            }
    except Exception:
        return None


def apply_automation_config_to_settings() -> None:
    """Push automation config from the default PRAgentConfig row into Dynaconf.

    Safe to call repeatedly; only known keys are written and values must be
    JSON-compatible. Missing DATABASE_URL or missing config row is a no-op.
    """
    if not os.environ.get("DATABASE_URL"):
        return

    config = _fetch_automation_config()
    if not config:
        return

    try:
        from pr_agent.config_loader import get_settings

        settings = get_settings()

        # Set the global flag unconditionally so toggling it OFF on the
        # dashboard reliably propagates to the webhook process (otherwise a
        # previous True value would linger in Dynaconf).
        settings.set("CONFIG.DISABLE_AUTO_FEEDBACK", bool(config.get("disable_auto_feedback")))

        for column, section in _AUTOMATION_SECTION_MAP.items():
            section_config = config.get(column) or {}
            if not isinstance(section_config, dict):
                continue
            for key in _AUTOMATION_ALLOWED_KEYS:
                if key not in section_config:
                    continue
                value = section_config[key]
                settings.set(f"{section}.{key.upper()}", value)
    except Exception:
        # Never break webhook processing if the refresh fails.
        pass


# TTL-cached refresh used by webhook handlers so dashboard changes take effect
# without requiring a webhook-service restart.
_last_refresh_at: float = 0.0
_refresh_lock = threading.Lock()


def ensure_postgres_config_loaded(ttl_seconds: float = 30.0) -> None:
    """Re-apply DB-backed credentials + automation config when TTL expires.

    Call this at the top of each webhook request handler. The first call after
    process start (or after TTL) reloads everything; subsequent calls are no-ops.
    """
    if not os.environ.get("DATABASE_URL"):
        return

    global _last_refresh_at
    now = time.monotonic()
    if now - _last_refresh_at < ttl_seconds:
        return

    with _refresh_lock:
        now = time.monotonic()
        if now - _last_refresh_at < ttl_seconds:
            return
        apply_postgres_credentials_to_config()
        _last_refresh_at = now


def invalidate_postgres_config_cache() -> None:
    """Force the next call to `ensure_postgres_config_loaded` to reload."""
    global _last_refresh_at
    _last_refresh_at = 0.0


# =============================================================================
# Knowledge-base config (/learn flag, extraction rules, retrieval tuning).
#
# Lives in the `knowledge_base_config` JSON column of the default PRAgentConfig
# row. The Dashboard writes this; `pr-agent` reads it here and overlays the
# values on the `KNOWLEDGE_BASE.*` Dynaconf section so runtime code keeps
# consulting a single source of truth (Dynaconf) even though the edits came
# from the database.
# =============================================================================

# Keys we surface through the Dashboard. Anything else in the JSON blob is
# ignored - we do not blindly forward keys to avoid clobbering infra-level
# settings such as `chroma_path` or `embedding_model`.
_KNOWLEDGE_BASE_ALLOWED_KEYS: tuple[str, ...] = (
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


def _fetch_knowledge_base_config() -> Optional[dict[str, Any]]:
    """Return the knowledge-base JSON dict from the default PRAgentConfig row.

    Returns ``None`` when DB is not configured, engine is not initialised, or
    no default config row exists. Returns an empty dict when the row exists
    but the column is NULL (meaning "use TOML defaults").
    """
    provider = get_postgres_credential_provider()
    provider._init_db()
    if not provider._initialized or not provider._engine:
        return None

    try:
        from sqlmodel import Session, select

        from pr_agent.db.models import PRAgentConfig

        with Session(provider._engine) as session:
            statement = (
                select(PRAgentConfig)
                .where(PRAgentConfig.is_default == True)  # noqa: E712
                .limit(1)
            )
            config = session.exec(statement).first()
            if not config:
                return None
            return dict(config.knowledge_base_config or {})
    except Exception:
        return None


def apply_knowledge_base_config_to_settings() -> None:
    """Overlay DB-stored knowledge-base config onto Dynaconf's KNOWLEDGE_BASE.*

    Only the allow-listed keys are written. Values that fail type coercion are
    dropped silently so a malformed row never crashes webhook processing.
    """
    if not os.environ.get("DATABASE_URL"):
        return

    kb_config = _fetch_knowledge_base_config()
    if kb_config is None:
        return

    try:
        from pr_agent.config_loader import get_settings

        settings = get_settings()
        for key in _KNOWLEDGE_BASE_ALLOWED_KEYS:
            if key not in kb_config:
                continue
            value = kb_config[key]
            # Coerce list-ish values for extraction_rules so we never push a
            # non-iterable into Dynaconf (defensive; the API validates too).
            if key == "extraction_rules":
                if value is None:
                    value = []
                elif not isinstance(value, (list, tuple)):
                    continue
                value = [str(v) for v in value if isinstance(v, str)]
            settings.set(f"KNOWLEDGE_BASE.{key.upper()}", value)
    except Exception:
        pass
