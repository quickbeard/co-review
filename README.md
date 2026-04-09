# CoReview

AI-powered code review tool with a dashboard for managing git provider credentials.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Compose Stack                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      PostgreSQL                          │  │
│  │                        :5432                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   PR-Agent (Python)                      │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   API       │  │   GitHub    │  │     GitLab      │  │   │
│  │  │   :3001     │  │   :3002     │  │     :3003       │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             ▲                                   │
│                             │ REST API                          │
│                             │                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Dashboard (Next.js)                      │   │
│  │                       :3000                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**How it works:**
1. Users configure git provider credentials via the Dashboard UI
2. Dashboard calls PR-Agent API to store/retrieve credentials
3. PR-Agent stores credentials in PostgreSQL (using SQLModel)
4. PR-Agent CLI/webhooks read credentials from the database
5. When a PR/MR is opened, PR-Agent performs automated code review

## Quick Start with Docker Compose

### Prerequisites

- Docker & Docker Compose
- Git

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values (defaults work for local development)
```

### 2. Configure LLM Provider

Create `pr-agent/pr_agent/settings/.secrets.toml`:

```toml
[openai]
key = "sk-..."  # or use other LLM providers
```

### 3. Start Services

```bash
# Start all services (database + API + dashboard)
docker compose up -d

# Enable GitHub webhook handler
docker compose --profile github up -d

# Or enable GitLab webhook handler
docker compose --profile gitlab up -d
```

### 4. Access the Dashboard

Open [http://localhost:3000](http://localhost:3000) to configure git providers.

## Quick Start with CLI (Local Development)

### Prerequisites

- Python 3.12+
- Node.js 18+ and Bun
- Docker (for PostgreSQL)

### 1. Start PostgreSQL

```bash
# Start only the database
docker compose up -d postgres

# Create database (first time only)
docker exec co-review-postgres psql -U postgres -c "CREATE DATABASE pr_agent;"
```

### 2. Start PR-Agent API

```bash
cd pr-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start API server
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pr_agent \
  python -m pr_agent.servers.api
```

API runs on http://localhost:3001

### 3. Start Dashboard

```bash
cd dashboard

# Install dependencies
bun install

# Start dev server
bun dev
```

Dashboard runs on http://localhost:3000

### 4. Configure Git Provider

1. Open http://localhost:3000
2. Go to "Git Providers" and add your GitHub/GitLab credentials
3. Save the provider configuration

### 5. Run PR-Agent CLI

```bash
cd pr-agent
source .venv/bin/activate

# Run a review (credentials loaded from database)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pr_agent \
  pr-agent --pr_url https://github.com/owner/repo/pull/123 review

# Other commands: describe, improve, ask
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pr_agent \
  pr-agent --pr_url https://github.com/owner/repo/pull/123 describe
```

## Services

| Service        | Port | Description                        |
| -------------- | ---- | ---------------------------------- |
| `postgres`     | 5432 | PostgreSQL database                |
| `pr-agent-api` | 3001 | REST API for credential management |
| `dashboard`    | 3000 | Next.js web UI                     |

### Optional Services (Profiles)

| Profile  | Service           | Port | Description            |
| -------- | ----------------- | ---- | ---------------------- |
| `github` | `pr-agent-github` | 3002 | GitHub webhook handler |
| `gitlab` | `pr-agent-gitlab` | 3003 | GitLab webhook handler |

## API Endpoints

The PR-Agent API provides these endpoints for git provider management:

```
GET    /health                  # Health check
GET    /api/providers           # List all providers
GET    /api/providers/{id}      # Get provider by ID
POST   /api/providers           # Create provider
PUT    /api/providers/{id}      # Update provider
PATCH  /api/providers/{id}      # Partial update (e.g., toggle status)
DELETE /api/providers/{id}      # Delete provider
```

## Docker Commands

```bash
# Start services
docker compose up -d

# Start with GitHub webhook handler
docker compose --profile github up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f pr-agent-api

# Stop services
docker compose down

# Stop and remove volumes (reset database)
docker compose down -v

# Rebuild after code changes
docker compose build --no-cache
docker compose up -d
```

## Environment Variables

### Docker/Database

| Variable            | Default                                                 | Description                  |
| ------------------- | ------------------------------------------------------- | ---------------------------- |
| `POSTGRES_USER`     | `postgres`                                              | PostgreSQL username          |
| `POSTGRES_PASSWORD` | `postgres`                                              | PostgreSQL password          |
| `POSTGRES_DB`       | `pr_agent`                                              | PostgreSQL database name     |
| `DATABASE_URL`      | `postgresql://postgres:postgres@postgres:5432/pr_agent` | Full database connection URL |
| `API_HOST`          | `0.0.0.0`                                               | API server bind address      |
| `API_PORT`          | `3001`                                                  | API server port              |

## Secrets & Configuration Reference

PR-Agent uses `.secrets.toml` for credentials and `configuration.toml` for settings. These can be managed via the Dashboard UI once configured, storing values in PostgreSQL.

### LLM Providers

| Provider              | Variable                | Required | Description                                       |
| --------------------- | ----------------------- | -------- | ------------------------------------------------- |
| **OpenAI**            | `key`                   | Yes      | API key from platform.openai.com                  |
|                       | `org`                   | No       | Organization ID for team accounts                 |
|                       | `api_type`              | No       | Set to `"azure"` for Azure OpenAI                 |
|                       | `api_version`           | No       | Azure API version (e.g., `2023-05-15`)            |
|                       | `api_base`              | No       | Custom endpoint URL (Azure or proxy)              |
|                       | `deployment_id`         | No       | Azure deployment name                             |
|                       | `fallback_deployments`  | No       | Backup deployment IDs if primary fails            |
| **Anthropic**         | `key`                   | Yes      | Claude API key from anthropic.com                 |
| **Cohere**            | `key`                   | Yes      | API key from dashboard.cohere.ai                  |
| **Replicate**         | `key`                   | Yes      | API key from replicate.com                        |
| **Groq**              | `key`                   | Yes      | API key from console.groq.com                     |
| **xAI**               | `key`                   | Yes      | Grok API key from console.x.ai                    |
| **HuggingFace**       | `key`                   | Yes      | Inference API token                               |
|                       | `api_base`              | Yes      | Your inference endpoint URL                       |
| **Ollama**            | `api_base`              | Yes      | Endpoint URL (`http://localhost:11434` for local) |
|                       | `api_key`               | No       | Required only for Ollama Cloud                    |
| **VertexAI**          | `vertex_project`        | Yes      | Google Cloud project name                         |
|                       | `vertex_location`       | Yes      | GCP region (e.g., `us-central1`)                  |
| **Google AI Studio**  | `gemini_api_key`        | Yes      | Gemini API key                                    |
| **DeepSeek**          | `key`                   | Yes      | DeepSeek API key                                  |
| **DeepInfra**         | `key`                   | Yes      | DeepInfra API key                                 |
| **Azure AD**          | `client_id`             | Yes      | Azure AD app client ID                            |
|                       | `client_secret`         | Yes      | Azure AD app secret                               |
|                       | `tenant_id`             | Yes      | Azure AD tenant ID                                |
|                       | `api_base`              | Yes      | Azure OpenAI service URL                          |
| **OpenRouter**        | `key`                   | Yes      | OpenRouter API key                                |
|                       | `api_base`              | No       | Custom endpoint                                   |
| **AWS Bedrock**       | `AWS_ACCESS_KEY_ID`     | Yes      | AWS access key                                    |
|                       | `AWS_SECRET_ACCESS_KEY` | Yes      | AWS secret key                                    |
|                       | `AWS_REGION_NAME`       | Yes      | AWS region (e.g., `us-east-1`)                    |
| **AWS Secrets Mgr**   | `secret_arn`            | Yes      | ARN of secret containing PR-Agent config          |
|                       | `region_name`           | No       | Override region                                   |
| **LiteLLM**           | `extra_body`            | No       | JSON for custom params (e.g., flex processing)    |
|                       | `model_id`              | No       | Custom inference profile ID                       |

### Git Providers

| Provider                 | Variable                | Required    | Description                             |
| ------------------------ | ----------------------- | ----------- | --------------------------------------- |
| **GitHub**               | `deployment_type`       | Yes         | `"user"` (PAT) or `"app"` (GitHub App)  |
|                          | `user_token`            | User mode   | Personal access token with `repo` scope |
|                          | `app_id`                | App mode    | GitHub App ID                           |
|                          | `private_key`           | App mode    | GitHub App private key (PEM format)     |
|                          | `webhook_secret`        | No          | Secret for verifying webhook payloads   |
| **GitLab**               | `personal_access_token` | Yes         | PAT with `api` scope                    |
|                          | `shared_secret`         | No          | Webhook verification secret             |
| **Gitea**                | `personal_access_token` | Yes         | Gitea access token                      |
|                          | `webhook_secret`        | No          | Webhook verification secret             |
| **Bitbucket**            | `auth_type`             | Yes         | `"bearer"` or `"basic"`                 |
|                          | `bearer_token`          | Bearer mode | OAuth2 bearer token                     |
|                          | `basic_token`           | Basic mode  | Basic auth token                        |
| **Bitbucket Server**     | `bearer_token`          | Yes         | Server bearer token                     |
|                          | `webhook_secret`        | No          | Webhook verification                    |
|                          | `app_key`               | No          | For Bitbucket app integration           |
|                          | `url`                   | No          | Server URL                              |
| **Azure DevOps**         | `org`                   | Yes         | Organization name                       |
|                          | `pat`                   | Yes         | Personal access token                   |
| **Azure DevOps Server**  | `webhook_username`      | No          | Basic auth username for webhooks        |
|                          | `webhook_password`      | No          | Basic auth password for webhooks        |

### Vector Databases (for Similar Issues feature)

| Provider     | Variable      | Required | Description                         |
| ------------ | ------------- | -------- | ----------------------------------- |
| **Pinecone** | `api_key`     | Yes      | Pinecone API key                    |
|              | `environment` | Yes      | Environment (e.g., `gcp-starter`)   |
| **Qdrant**   | `url`         | Yes      | Qdrant Cloud or self-hosted URL     |
|              | `api_key`     | Yes      | Qdrant API key                      |
| **LanceDB**  | `uri`         | Yes      | Local path (e.g., `./lancedb`)      |

### PR-Agent Configuration Settings

**General Config:**

| Variable            | Default   | Description                                     |
| ------------------- | --------- | ----------------------------------------------- |
| `model`             | `gpt-4`   | Primary LLM model                               |
| `fallback_models`   | `[]`      | Backup models if primary fails                  |
| `git_provider`      | `github`  | Default git provider                            |
| `ai_timeout`        | `120`     | Request timeout in seconds                      |
| `temperature`       | `0.2`     | Model creativity (0-2)                          |
| `max_model_tokens`  | `32000`   | Max tokens per request                          |
| `response_language` | `en-US`   | Output language (ISO format)                    |
| `verbosity_level`   | `0`       | Log verbosity (0-2)                             |
| `reasoning_effort`  | `medium`  | For reasoning models (`low`/`medium`/`high`)    |

**Ignore Patterns:**

| Variable                   | Description                          |
| -------------------------- | ------------------------------------ |
| `ignore_pr_title`          | Regex patterns to skip PRs by title  |
| `ignore_pr_target_branches`| Skip PRs targeting these branches    |
| `ignore_pr_source_branches`| Skip PRs from these branches         |
| `ignore_pr_labels`         | Skip PRs with these labels           |
| `ignore_pr_authors`        | Skip PRs from these authors          |
| `ignore_repositories`      | Skip these repos entirely            |

## Project Structure

```
co-review/
├── dashboard/              # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   └── lib/api/           # API client for PR-Agent
├── pr-agent/              # Python backend
│   ├── pr_agent/
│   │   ├── db/            # SQLModel models & database
│   │   ├── servers/       # FastAPI servers (api.py, github_app.py, etc.)
│   │   ├── secret_providers/  # Credential providers (postgres, aws, etc.)
│   │   ├── tools/         # Review tools
│   │   └── settings/      # Configuration
│   └── docker/            # Dockerfiles
├── docker-compose.yml     # Service orchestration
├── .env.example           # Environment template
└── .env                   # Local environment (git-ignored)
```

## Database Schema

The PR-Agent API uses SQLModel with PostgreSQL. Four tables store all configuration:

### Tables Overview

| Table                 | Purpose                                                      |
| --------------------- | ------------------------------------------------------------ |
| `git_providers`       | Git provider credentials (GitHub, GitLab, Bitbucket, etc.)   |
| `llm_providers`       | LLM API credentials (OpenAI, Anthropic, VertexAI, etc.)      |
| `vector_db_providers` | Vector DB credentials for similar issues (Pinecone, Qdrant)  |
| `pr_agent_configs`    | PR-Agent configuration profiles                              |

### git_providers

```python
class GitProvider(SQLModel, table=True):
    id: int                    # Primary key
    type: GitProviderType      # github, gitlab, bitbucket, azure_devops, gitea, gerrit
    name: str                  # Display name
    base_url: str | None       # For self-hosted instances
    is_active: bool
    is_default: bool
    # GitHub
    deployment_type: str | None  # user or app
    access_token: str | None     # PAT or bearer token
    app_id: str | None
    private_key: str | None
    webhook_secret: str | None
    # Bitbucket
    auth_type: str | None        # bearer or basic
    basic_token: str | None
    app_key: str | None
    # Azure DevOps
    organization: str | None
    pat: str | None
    webhook_username: str | None
    webhook_password: str | None
    # Gerrit
    gerrit_user: str | None
    patch_server_endpoint: str | None
    patch_server_token: str | None
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### llm_providers

```python
class LLMProvider(SQLModel, table=True):
    id: int                    # Primary key
    type: LLMProviderType      # openai, anthropic, vertexai, azure_openai, etc.
    name: str                  # Display name
    is_active: bool
    is_default: bool
    # Common
    api_key: str | None
    api_base: str | None
    # OpenAI/Azure
    organization: str | None
    api_type: str | None       # openai or azure
    api_version: str | None
    deployment_id: str | None
    fallback_deployments: str | None
    # Azure AD
    client_id: str | None
    client_secret: str | None
    tenant_id: str | None
    # VertexAI
    vertex_project: str | None
    vertex_location: str | None
    # AWS
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_region_name: str | None
    # LiteLLM
    extra_body: str | None
    model_id: str | None
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### vector_db_providers

```python
class VectorDBProvider(SQLModel, table=True):
    id: int                    # Primary key
    type: VectorDBType         # pinecone, qdrant, lancedb
    name: str                  # Display name
    is_active: bool
    is_default: bool
    api_key: str | None
    url: str | None            # Service URL
    environment: str | None    # Pinecone environment
    uri: str | None            # LanceDB local path
    created_at: datetime
    updated_at: datetime
```

### pr_agent_configs

```python
class PRAgentConfig(SQLModel, table=True):
    id: int                    # Primary key
    name: str                  # Profile name
    is_active: bool
    is_default: bool
    # General settings
    model: str                 # Primary LLM model
    fallback_models: str | None
    git_provider: str
    ai_timeout: int
    temperature: float
    max_model_tokens: int
    response_language: str
    # Tool configs (JSON)
    pr_reviewer_config: dict | None
    pr_description_config: dict | None
    pr_code_suggestions_config: dict | None
    github_app_config: dict | None
    gitlab_config: dict | None
    # ... other tool/provider configs
    # Ignore patterns (JSON arrays)
    ignore_pr_title: list[str] | None
    ignore_pr_labels: list[str] | None
    ignore_repositories: list[str] | None
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

## Credential Priority

PR-Agent loads credentials in this order:
1. **PostgreSQL database** (if `DATABASE_URL` is set) - managed via Dashboard
2. **`.secrets.toml`** - fallback for local development
