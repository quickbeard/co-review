"""
PostgreSQL Secret Provider for PR-Agent

Loads git provider credentials from a PostgreSQL database shared with the Dashboard.
This is used when PR-Agent is deployed alongside the Dashboard application.
"""
import os
import time
from typing import Optional

from pr_agent.log import get_logger
from pr_agent.secret_providers.secret_provider import SecretProvider


class PostgresSecretProvider(SecretProvider):
    """
    Loads git provider credentials from PostgreSQL database.
    Used when PR-Agent is deployed with the Dashboard.

    Database schema expected (from Dashboard's Prisma schema):

    GitProvider table:
        - id: TEXT PRIMARY KEY
        - type: TEXT (github, gitlab, bitbucket, etc.)
        - name: TEXT
        - baseUrl: TEXT (for self-hosted instances)
        - accessToken: TEXT
        - webhookSecret: TEXT
        - isActive: BOOLEAN
        - organizationId: TEXT

    Repository table:
        - id: TEXT PRIMARY KEY
        - fullName: TEXT (e.g., "org/repo")
        - gitProviderId: TEXT (foreign key)
        - isActive: BOOLEAN
        - settings: JSONB (per-repo PR-Agent settings)
    """

    # Cache TTL in seconds
    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self._connection = None
        self._cache: dict[str, tuple[dict, float]] = {}  # key -> (value, timestamp)
        self._connect()

    def _connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as e:
            raise ImportError(
                "psycopg2 is required for PostgreSQL secret provider. "
                "Install it with: pip install psycopg2-binary"
            ) from e

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required for PostgreSQL secret provider"
            )

        try:
            self._connection = psycopg2.connect(database_url)
            self._connection.autocommit = True
            get_logger().info("PostgreSQL secret provider connected successfully")
        except Exception as e:
            get_logger().error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def _ensure_connection(self):
        """Ensure the database connection is alive, reconnect if needed."""
        if self._connection is None or self._connection.closed:
            get_logger().info("PostgreSQL connection lost, reconnecting...")
            self._connect()

    def _get_cached(self, cache_key: str) -> Optional[dict]:
        """Get value from cache if not expired."""
        if cache_key in self._cache:
            value, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.CACHE_TTL:
                return value
            else:
                del self._cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, value: dict):
        """Store value in cache."""
        self._cache[cache_key] = (value, time.time())

    def get_secret(self, secret_name: str) -> str:
        """
        Retrieve individual secret by name.

        For backwards compatibility with the SecretProvider interface.
        This method is less useful for git credentials which require
        multiple values (token, base_url, etc.).
        """
        # Not implemented for postgres provider as we use get_git_credentials instead
        get_logger().warning(
            f"get_secret() called on PostgresSecretProvider with name '{secret_name}'. "
            "Use get_git_credentials() for git provider credentials."
        )
        return ""

    def store_secret(self, secret_name: str, secret_value: str):
        """Store a secret. Not implemented for PostgresSecretProvider."""
        raise NotImplementedError(
            "PostgresSecretProvider is read-only. "
            "Use the Dashboard to manage git provider credentials."
        )

    def get_git_credentials(
        self,
        provider_type: str,
        repo_full_name: Optional[str] = None
    ) -> Optional[dict]:
        """
        Look up credentials for a git provider, optionally for a specific repository.

        Args:
            provider_type: Git provider type ('github', 'gitlab', 'bitbucket', etc.)
            repo_full_name: Repository full name in 'org/repo' format (optional).
                           If provided, looks up the specific repository's git provider.
                           If not provided, returns the first active provider of that type.

        Returns:
            Dictionary with credentials:
            {
                'token': 'ghp_xxx',
                'base_url': 'https://api.github.com',
                'webhook_secret': '...',
                'provider_id': '...',
                'repo_settings': {...},  # Per-repo settings override (if repo_full_name provided)
            }
            Returns None if no matching provider found.
        """
        cache_key = f"{provider_type}:{repo_full_name or '*'}"

        # Check cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            get_logger().debug(f"Using cached credentials for {cache_key}")
            return cached

        try:
            self._ensure_connection()

            from psycopg2.extras import RealDictCursor

            with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                if repo_full_name:
                    # Look up by repository full name
                    result = self._get_credentials_by_repo(cursor, provider_type, repo_full_name)
                else:
                    # Look up first active provider of this type
                    result = self._get_credentials_by_type(cursor, provider_type)

                if result:
                    # Never log the actual token
                    get_logger().info(
                        f"Loaded git credentials for {provider_type}"
                        f"{f' (repo: {repo_full_name})' if repo_full_name else ''}"
                    )
                    self._set_cached(cache_key, result)
                    return result
                else:
                    get_logger().warning(
                        f"No active git provider found for type '{provider_type}'"
                        f"{f' and repo '{repo_full_name}'' if repo_full_name else ''}"
                    )
                    return None

        except Exception as e:
            get_logger().error(f"Failed to get git credentials from PostgreSQL: {e}")
            return None

    def _get_credentials_by_repo(self, cursor, provider_type: str, repo_full_name: str) -> Optional[dict]:
        """Get credentials for a specific repository."""
        query = """
            SELECT
                gp.id as provider_id,
                gp.type,
                gp."accessToken" as token,
                gp."baseUrl" as base_url,
                gp."webhookSecret" as webhook_secret,
                r.settings as repo_settings
            FROM "Repository" r
            JOIN "GitProvider" gp ON r."gitProviderId" = gp.id
            WHERE r."fullName" = %s
              AND gp.type = %s
              AND gp."isActive" = true
              AND r."isActive" = true
            LIMIT 1
        """
        cursor.execute(query, (repo_full_name, provider_type))
        row = cursor.fetchone()

        if row:
            return self._format_credentials(row)
        return None

    def _get_credentials_by_type(self, cursor, provider_type: str) -> Optional[dict]:
        """Get credentials for first active provider of given type."""
        query = """
            SELECT
                id as provider_id,
                type,
                "accessToken" as token,
                "baseUrl" as base_url,
                "webhookSecret" as webhook_secret
            FROM "GitProvider"
            WHERE type = %s
              AND "isActive" = true
            ORDER BY "createdAt" ASC
            LIMIT 1
        """
        cursor.execute(query, (provider_type,))
        row = cursor.fetchone()

        if row:
            return self._format_credentials(row)
        return None

    def _format_credentials(self, row: dict) -> dict:
        """Format database row into credentials dictionary."""
        result = {
            'token': row['token'],
            'base_url': row.get('base_url'),
            'webhook_secret': row.get('webhook_secret'),
            'provider_id': row['provider_id'],
        }

        # Include repo settings if present
        if 'repo_settings' in row and row['repo_settings']:
            result['repo_settings'] = row['repo_settings']

        return result

    def get_repo_settings(self, provider_type: str, repo_full_name: str) -> Optional[dict]:
        """
        Get repository-specific PR-Agent settings override.

        Args:
            provider_type: Git provider type
            repo_full_name: Repository full name in 'org/repo' format

        Returns:
            Dictionary with settings override, or None if not found.
        """
        credentials = self.get_git_credentials(provider_type, repo_full_name)
        if credentials and 'repo_settings' in credentials:
            return credentials['repo_settings']
        return None

    def clear_cache(self):
        """Clear the credentials cache."""
        self._cache.clear()
        get_logger().debug("PostgreSQL credentials cache cleared")

    def close(self):
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            get_logger().debug("PostgreSQL connection closed")


# Singleton instance for the provider
_postgres_provider_instance: Optional[PostgresSecretProvider] = None


def get_postgres_secret_provider() -> PostgresSecretProvider:
    """Get or create the singleton PostgresSecretProvider instance."""
    global _postgres_provider_instance
    if _postgres_provider_instance is None:
        _postgres_provider_instance = PostgresSecretProvider()
    return _postgres_provider_instance
