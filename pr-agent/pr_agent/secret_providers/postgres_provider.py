"""
PostgreSQL Credential Provider for PR-Agent.

Reads git provider and LLM provider credentials from PostgreSQL database (stored via Dashboard).
Falls back to .secrets.toml if no matching provider is found in the database.
"""

import os
from typing import Optional

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

    except Exception:
        # Silently fail - fall back to .secrets.toml
        pass
