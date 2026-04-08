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

| Variable          | Default                                          | Description                    |
| ----------------- | ------------------------------------------------ | ------------------------------ |
| `POSTGRES_USER`   | `postgres`                                       | PostgreSQL username            |
| `POSTGRES_PASSWORD` | `postgres`                                     | PostgreSQL password            |
| `POSTGRES_DB`     | `pr_agent`                                       | PostgreSQL database name       |
| `DATABASE_URL`    | `postgresql://postgres:postgres@postgres:5432/pr_agent` | Full database connection URL |

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

## Credential Priority

PR-Agent loads credentials in this order:
1. **PostgreSQL database** (if `DATABASE_URL` is set) - managed via Dashboard
2. **`.secrets.toml`** - fallback for local development
