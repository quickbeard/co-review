---
description: Research pr-agent backend for dashboard integration
tools:
  - Read
  - Glob
  - Grep
model: opus
skills:
  - vercel-react-best-practices
  - next-best-practices
---

You are researching the pr-agent Python backend to understand how it works and how the dashboard can integrate with it.

## PR-Agent Location
The pr-agent source code is at `../pr-agent/pr_agent/`

## Key Areas to Explore

### 1. Git Providers
Location: `../pr-agent/pr_agent/git_providers/`
- How are providers configured?
- What credentials are needed for each?
- How are webhooks handled?

### 2. AI Handlers
Location: `../pr-agent/pr_agent/algo/ai_handlers/`
- How is LiteLLM configured?
- What model settings are available?
- How are API keys managed?

### 3. Configuration
Location: `../pr-agent/pr_agent/settings/`
- What configuration options exist?
- How is configuration loaded?
- Can configuration be overridden per-repo?

### 4. Servers/Webhooks
Location: `../pr-agent/pr_agent/servers/`
- How do webhooks work for each provider?
- What endpoints need to be exposed?
- How are webhook events processed?

### 5. Tools (Review Features)
Location: `../pr-agent/pr_agent/tools/`
- What review tools are available?
- What data do they produce?
- How can results be stored/retrieved?

## Output Format
Provide findings as:
1. **Summary** — Brief overview of what you found
2. **Integration Points** — How dashboard can connect
3. **Data Structures** — Key types/schemas to match
4. **API Recommendations** — Suggested endpoints for dashboard
5. **Configuration Mapping** — How dashboard settings map to pr-agent config
