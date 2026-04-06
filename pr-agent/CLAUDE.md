# PR-Agent Backend

This is the PR-Agent Python backend - an AI-powered code review tool.

## Quick Reference

- **Framework**: FastAPI 0.115+ with Starlette
- **Python**: 3.12+
- **Config**: Dynaconf (TOML files in `pr_agent/settings/`)
- **Entry points**: `pr_agent/servers/*.py`

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `pr_agent/servers/` | FastAPI webhook handlers (GitHub, GitLab, etc.) |
| `pr_agent/tools/` | Review tools (review, describe, improve) |
| `pr_agent/algo/ai_handlers/` | LLM integrations (LiteLLM) |
| `pr_agent/git_providers/` | Git platform abstractions |
| `pr_agent/settings/` | TOML configuration files |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run GitHub webhook server
python -m pr_agent.servers.github_app

# Run tests
PYTHONPATH=. pytest tests/unittest/ -v
```

## Dashboard Integration

This backend is being integrated with a Next.js dashboard. The dashboard needs:
- JSON API endpoints (not just webhook handlers)
- Structured review output (not just PR comments)
- Config override support per-request

See `.claude/agents/pr-agent-feature.md` for the integration API spec.
