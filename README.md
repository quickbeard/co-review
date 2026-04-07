# CoReview

AI-powered code review tool with a dashboard for managing git provider credentials. PR-Agent handles automated code reviews while the Dashboard provides a UI for configuration.

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
│                 │                          │                    │
│                 ▼                          ▼                    │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │   Dashboard (Next.js)   │  │   PR-Agent (webhook server) │  │
│  │         :3000           │  │      :3002 / :3003          │  │
│  │                         │  │                             │  │
│  │  - Manage git providers │  │  - GitHub/GitLab webhooks   │  │
│  │  - Store credentials    │  │  - Reads credentials from   │  │
│  │                         │  │    shared PostgreSQL        │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**How it works:**
1. Users configure git provider credentials (GitHub, GitLab, etc.) via the Dashboard UI
2. Credentials are stored in PostgreSQL
3. PR-Agent reads credentials from the same database using `PostgresSecretProvider`
4. When a PR/MR is opened, PR-Agent performs automated code review using the stored credentials

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

**Dashboard secrets** (`dashboard/.env`):

```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dashboard"
```

### 2. Start Services

```bash
# Start dashboard and database
docker compose up -d

# Enable GitHub webhook handler
docker compose --profile github up -d

# Or enable GitLab webhook handler
docker compose --profile gitlab up -d
```

### 3. Configure Git Providers

1. Open [http://localhost:3000](http://localhost:3000)
2. Navigate to Git Providers
3. Add your GitHub/GitLab credentials

## Services

| Service    | Port | Description                    |
| ---------- | ---- | ------------------------------ |
| `postgres` | 5432 | PostgreSQL database            |
| `dashboard`| 3000 | Next.js web UI for management  |

### Optional Services (Profiles)

Enable webhook handlers with `--profile <name>`:

| Profile  | Service           | Port | Description              |
| -------- | ----------------- | ---- | ------------------------ |
| `github` | `pr-agent-github` | 3002 | GitHub App webhook handler |
| `gitlab` | `pr-agent-gitlab` | 3003 | GitLab webhook handler     |

## Commands

```bash
# Start services
docker compose up -d

# Start with GitHub webhook handler
docker compose --profile github up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f dashboard

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
bun prisma generate
bun prisma migrate dev
bun run dev
```

### Run Tests

```bash
cd dashboard

# Unit tests
bun test:run

# E2E tests
bun test:e2e
```

### Run PR-Agent Locally

```bash
cd pr-agent
pip install -r requirements.txt

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
│   ├── lib/actions/       # Server actions
│   ├── prisma/            # Database schema & migrations
│   ├── tests/             # Unit tests (Vitest)
│   └── e2e/               # E2E tests (Playwright)
├── pr-agent/              # Python backend
│   ├── pr_agent/
│   │   ├── servers/       # Webhook handlers
│   │   ├── tools/         # Review tools
│   │   ├── secret_providers/
│   │   │   └── postgres_secret_provider.py  # Reads from Dashboard DB
│   │   └── settings/      # Configuration
│   └── docker/            # Dockerfiles
└── docker-compose.yml     # Service orchestration
```
