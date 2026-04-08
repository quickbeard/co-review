"""
PostgreSQL Credential Provider for PR-Agent.

Reads git provider credentials from PostgreSQL database (stored via Dashboard).
Falls back to .secrets.toml if no matching provider is found in the database.
"""

import os
from typing import Optional


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

    except Exception:
        # Silently fail - fall back to .secrets.toml
        pass
