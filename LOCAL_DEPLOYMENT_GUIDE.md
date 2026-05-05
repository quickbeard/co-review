# Local Deployment Guide (Simple)

This guide is the quickest way to run the current CoReview stack locally.

## 1) Prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Git
- [ngrok](https://ngrok.com/)
- A GitHub or GitLab account

## 2) Prepare environment

From repo root:

```bash
cp .env.example .env
```

Then edit `.env` and set at least:

- `OPENAI_API_KEY`
- `ENCRYPTION_SECRET` (required by DevLake)

You can keep the default local ports unless they conflict on your machine.

## 3) Start DevLake first

```bash
docker compose --profile devlake up -d
```

Verify DevLake is up:

- DevLake UI: [http://localhost:30090](http://localhost:30090)
- Grafana: [http://localhost:30090/grafana](http://localhost:30090/grafana)

If this is your first run, complete any initial DevLake setup in the UI.

## 3.1) Bootstrap shareable Grafana dashboards (one-time)

After DevLake is up, run:

```bash
./scripts/devlake-setup-grafana-dashboards.sh
```

The script duplicates the built-in DevLake GitHub/GitLab/Azure DevOps dashboards
into a `CoReview Dashboards` folder and prints env values.

Copy the generated lines into `.env`:

- `NEXT_PUBLIC_DEVLAKE_GRAFANA_BASE_URL=...`
- `NEXT_PUBLIC_DEVLAKE_GRAFANA_DASHBOARD_UID_MAP=github:...,gitlab:...,azure_devops:...`

Then restart the dashboard service if it is already running:

```bash
docker compose up -d dashboard
```

You can safely re-run this script any time (it updates/overwrites the same
CoReview dashboard UIDs instead of creating duplicates).

## 4) Start main stack

Choose one git provider profile (you can run both if needed):

```bash
# Base services + GitHub webhook service
docker compose --profile github up -d

# OR base services + GitLab webhook service
docker compose --profile gitlab up -d
```

Main URLs:

- Dashboard: [http://localhost:3000](http://localhost:3000)
- PR-Agent API: [http://localhost:3001/health](http://localhost:3001/health)

## 5) Expose webhook endpoint with ngrok

Start ngrok for the webhook service you use:

```bash
# GitHub webhook service (container port mapped to localhost:3002)
ngrok http 3002

# GitLab webhook service (container port mapped to localhost:3003)
ngrok http 3003
```

Copy the public ngrok URL (for example `https://xxxx.ngrok-free.app`).

## 6) Create provider token/app in Git platform

- **GitHub**
  - Easiest: create a PAT with repo permissions.
  - Optional: use GitHub App mode if your workflow requires it.
- **GitLab**
  - Use a Personal Access Token (`api` scope).
  - GitLab supports OAuth Apps and integrations, but for this local stack PAT is the simplest path.

## 7) Configure Git Provider in dashboard

1. Open [http://localhost:3000](http://localhost:3000)
2. Go to **Git Providers** -> **New Provider**
3. Select GitHub or GitLab, then fill credentials (PAT/app fields)
4. Save

Optional but recommended:

- Configure DevLake integration for that provider
- Validate and trigger first sync from the provider detail page

## 8) Configure repository webhooks

In dashboard:

1. Open your provider -> **Webhooks**
2. Add a webhook for your target repo
3. Use your ngrok URL + provider path:
   - GitLab: `https://<ngrok-domain>/webhook`
   - GitHub (PAT/user webhook mode): `https://<ngrok-domain>/api/v1/github_webhooks`
4. Register/test webhook and confirm deliveries are successful

## 9) Trigger PR-Agent review

- Open a PR (GitHub) or MR (GitLab) on a repo connected to the webhook.
- PR-Agent should auto-run based on configured automation commands.

## 10) Save learnings to Mem0/Chroma

- In PR/MR comments, use quote-reply / learning commands according to your team flow.
- Learnings are stored in shared Mem0/Chroma volume and reused in future reviews.

## Quick troubleshooting

- Check containers:
  ```bash
  docker compose ps
  ```
- Follow logs:
  ```bash
  docker compose logs -f pr-agent-api
  docker compose logs -f pr-agent-github
  docker compose logs -f pr-agent-gitlab
  docker compose logs -f dashboard
  ```
- If webhook delivery fails, verify:
  - ngrok is still running
  - correct endpoint path (`/webhook` or `/api/v1/github_webhooks`)
  - token/secret configuration matches both sides
