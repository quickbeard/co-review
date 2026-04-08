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
4. When a PR/MR is opened, PR-Agent performs automated code review

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### 1. Configure Secrets

**PR-Agent secrets** (`pr-agent/pr_agent/settings/.secrets.toml`):

```toml
[openai]
key = "sk-..."  # or use other LLM providers
```

### 2. Start Services

```bash
# Start all services (database + API + dashboard)
docker compose up -d

# Enable GitHub webhook handler
docker compose --profile github up -d

# Or enable GitLab webhook handler
docker compose --profile gitlab up -d
```

### 3. Access the Dashboard

Open [http://localhost:3000](http://localhost:3000)

## Services

| Service        | Port | Description                    |
| -------------- | ---- | ------------------------------ |
| `postgres`     | 5432 | PostgreSQL database            |
| `pr-agent-api` | 3001 | REST API for credential management |
| `dashboard`    | 3000 | Next.js web UI                 |

### Optional Services (Profiles)

| Profile  | Service           | Port | Description              |
| -------- | ----------------- | ---- | ------------------------ |
| `github` | `pr-agent-github` | 3002 | GitHub webhook handler   |
| `gitlab` | `pr-agent-gitlab` | 3003 | GitLab webhook handler   |

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

## Commands

```bash
# Start services
docker compose up -d

# Start with GitHub webhook handler
docker compose --profile github up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Stop and remove volumes (reset data)
docker compose down -v

# Rebuild after code changes
docker compose build --no-cache
docker compose up -d
```

## Development

### Run Dashboard Locally

```bash
cd dashboard
bun install
bun run dev
```

### Run PR-Agent API Locally

```bash
cd pr-agent

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker compose up -d postgres

# Create database (first time only)
docker exec co-review-postgres psql -U postgres -c "CREATE DATABASE pr_agent;"

# Run API server
python -m pr_agent.servers.api
```

### Run Webhook Servers Locally

```bash
cd pr-agent

# GitHub webhook server
python -m pr_agent.servers.github_app

# GitLab webhook server
python -m pr_agent.servers.gitlab_webhook
```

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
│   │   ├── tools/         # Review tools
│   │   └── settings/      # Configuration
│   └── docker/            # Dockerfiles
└── docker-compose.yml     # Service orchestration
```

## Database Schema

The PR-Agent API uses SQLModel with PostgreSQL:

```python
class GitProvider(SQLModel, table=True):
    id: int (primary key)
    type: str              # github, gitlab, bitbucket, etc.
    name: str              # Display name
    base_url: str | None   # For self-hosted instances
    access_token: str | None
    deployment_type: str | None  # For GitHub: user or app
    app_id: str | None     # GitHub App ID
    private_key: str | None # GitHub App private key
    webhook_secret: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
```
