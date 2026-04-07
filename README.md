# CoReview

AI-powered code review tool that acts as an automated, senior-level reviewer for pull requests (PRs) in git platforms like GitHub and GitLab.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  PostgreSQL │  │    Redis    │  │    PR-Agent API     │ │
│  │    :5432    │  │    :6379    │  │       :3001         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│         │                │                   │              │
│         └────────────────┴───────────────────┘              │
│                          │                                  │
│                          ▼                                  │
│              ┌───────────────────────┐                      │
│              │   Dashboard (Next.js) │                      │
│              │         :3000         │                      │
│              └───────────────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### 1. Configure Secrets

**PR-Agent secrets** (`pr-agent/pr_agent/settings/.secrets.toml`):

```toml
[openai]
key = "sk-..."  # or use other LLM providers

[github]
user_token = "ghp_..."
deployment_type = "user"
```

**Dashboard secrets** (`dashboard/.env`):

```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dashboard"
```

### 2. Start All Services

```bash
docker compose up -d
```

> **Note**: Database migrations run automatically when the dashboard starts.

### 3. Access the Dashboard

Open [http://localhost:3000](http://localhost:3000)

## Services

| Service        | Port | Description         |
| -------------- | ---- | ------------------- |
| `dashboard`    | 3000 | Next.js web UI      |
| `pr-agent-api` | 3001 | PR-Agent REST API   |
| `postgres`     | 5432 | PostgreSQL database |
| `redis`        | 6379 | Redis (job queue)   |

### Optional Services (Profiles)

Enable with `--profile <name>`:

```bash
# GitHub webhook handler
docker compose --profile github up -d

# GitLab webhook handler
docker compose --profile gitlab up -d
```

| Profile  | Service           | Port | Description         |
| -------- | ----------------- | ---- | ------------------- |
| `github` | `pr-agent-github` | 3002 | GitHub App webhooks |
| `gitlab` | `pr-agent-gitlab` | 3003 | GitLab webhooks     |

## Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f dashboard pr-agent-api

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
bunx prisma generate
bun run dev
```

### Run PR-Agent API Locally

```bash
cd pr-agent
pip install -r requirements.txt
python -m pr_agent.servers.dashboard_api
```

## Project Structure

```
co-review/
├── dashboard/           # Next.js frontend
│   ├── app/            # App router pages
│   ├── components/     # React components
│   └── prisma/         # Database schema
├── pr-agent/           # Python backend
│   ├── pr_agent/
│   │   ├── servers/    # FastAPI endpoints
│   │   ├── tools/      # Review tools
│   │   └── settings/   # Configuration
│   └── docker/         # Dockerfiles
└── docker-compose.yml  # Service orchestration
```
