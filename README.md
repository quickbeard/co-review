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
│                             │ API calls                         │
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
3. PR-Agent stores credentials in PostgreSQL
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
# Start all services
docker compose up -d

# Enable GitHub webhook handler
docker compose --profile github up -d

# Or enable GitLab webhook handler
docker compose --profile gitlab up -d
```

### 3. Access the Dashboard

Open [http://localhost:3000](http://localhost:3000)

## Services

| Service    | Port | Description         |
| ---------- | ---- | ------------------- |
| `postgres` | 5432 | PostgreSQL database |
| `dashboard`| 3000 | Next.js web UI      |

### Optional Services (Profiles)

| Profile  | Service           | Port | Description              |
| -------- | ----------------- | ---- | ------------------------ |
| `github` | `pr-agent-github` | 3002 | GitHub webhook handler   |
| `gitlab` | `pr-agent-gitlab` | 3003 | GitLab webhook handler   |

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
│   └── lib/               # Utilities
├── pr-agent/              # Python backend
│   ├── pr_agent/
│   │   ├── servers/       # Webhook handlers + API
│   │   ├── tools/         # Review tools
│   │   └── settings/      # Configuration
│   └── docker/            # Dockerfiles
└── docker-compose.yml     # Service orchestration
```

## Status

- [x] Dashboard UI shell (Next.js)
- [x] PR-Agent webhook handlers (GitHub, GitLab)
- [ ] PR-Agent API for credential management
- [ ] Dashboard integration with PR-Agent API
