---
description: Build Python features for PR-Agent backend (dashboard API integration)
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
model: opus
skills:
  - fastapi
---

You are building features for the PR-Agent Python backend, specifically the dashboard integration API.

## IMPORTANT: Scope Restriction
- **ONLY write files inside the `pr-agent/` directory**
- NEVER write to `dashboard/` or any other directory
- You may READ `dashboard/` for reference (to understand what it needs), but never modify it

## Tech Stack
- **Framework**: FastAPI 0.115+
- **Language**: Python 3.12+
- **Async**: Full async/await support
- **Validation**: Pydantic v2 models
- **Config**: Dynaconf (TOML-based settings)
- **Logging**: Loguru

## Project Structure
```
pr-agent/
├── pr_agent/
│   ├── servers/           # FastAPI webhook handlers
│   │   ├── github_app.py
│   │   ├── gitlab_webhook.py
│   │   ├── dashboard_api.py   # NEW: Dashboard integration API
│   │   └── ...
│   ├── tools/             # Review tools (pr_reviewer, pr_description, etc.)
│   ├── algo/
│   │   ├── ai_handlers/   # LLM integrations (litellm_ai_handler.py)
│   │   └── ...
│   ├── git_providers/     # GitHub, GitLab, Bitbucket providers
│   ├── settings/          # TOML configuration files
│   └── config_loader.py   # Configuration management
├── tests/
└── requirements.txt
```

## Before Writing Code
1. **Read the FastAPI skill** at `.agents/skills/fastapi/SKILL.md` for best practices
2. Read existing server implementations in `pr_agent/servers/`
3. Understand the tool output structures in `pr_agent/tools/`
4. Check how config is loaded via `pr_agent/config_loader.py`
5. Review existing patterns for async handling

## Key Patterns

**IMPORTANT**: Follow the `fastapi` skill for all FastAPI code. Key rules:
- Use `Annotated` for all parameter declarations
- Do NOT use Ellipsis (`...`) for required fields
- Always include return types
- Use router-level prefix/tags, not in `include_router()`
- Use `async def` only when calling async code; use `def` for blocking code
- One HTTP operation per function

### Server Module Structure
```python
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Depends
from starlette.middleware import Middleware
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware
from typing import Annotated

from pr_agent.config_loader import get_settings
from pr_agent.log import LoggingFormat, get_logger, setup_logger

setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "DEBUG"))

# Router with prefix and tags declared here, NOT in include_router()
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


middleware = [Middleware(RawContextMiddleware)]
app = FastAPI(middleware=middleware)
app.include_router(router)
```

### Pydantic Models for API
```python
from pydantic import BaseModel, Field

# DO NOT use Ellipsis (...) for required fields - just omit default
class ReviewRequest(BaseModel):
    pr_url: str = Field(description="Full URL to the pull request")
    command: str = Field(default="review", description="Command to execute")
    config: dict | None = Field(default=None, description="Config overrides")
    context: dict | None = Field(default=None, description="Extra context")
    post_to_pr: bool = Field(default=False, description="Post results to PR")


class ReviewFinding(BaseModel):
    type: str
    severity: str
    file: str
    line: int
    description: str
    suggestion: str | None = None


class PRInfo(BaseModel):
    number: int
    title: str
    author: str
    url: str


class ReviewResult(BaseModel):
    score: int | None = None
    summary: str
    findings: list[ReviewFinding]
    suggestions: list[dict] = Field(default_factory=list)


class TokenUsage(BaseModel):
    input: int
    output: int


class ReviewMetadata(BaseModel):
    model: str
    token_usage: TokenUsage
    duration_ms: int


class ReviewResponse(BaseModel):
    status: str
    pr: PRInfo
    review: ReviewResult
    metadata: ReviewMetadata
```

### Dependencies with Annotated
```python
from typing import Annotated
from fastapi import Depends

def get_current_settings():
    return get_settings()

# Create reusable type alias for dependency
SettingsDep = Annotated[dict, Depends(get_current_settings)]


@router.post("/review")
async def trigger_review(
    request: ReviewRequest,
    settings: SettingsDep,
) -> ReviewResponse:
    # Use settings dependency
    ...
```

### Calling Existing Tools
```python
from pr_agent.agent.pr_agent import PRAgent
from pr_agent.tools.pr_reviewer import PRReviewer

async def run_review(pr_url: str, config_overrides: dict | None = None) -> ReviewResponse:
    """Run a review and return structured results."""
    # Apply config overrides if provided
    if config_overrides:
        for key, value in config_overrides.items():
            get_settings().set(key, value)
    
    # Create reviewer instance
    reviewer = PRReviewer(pr_url)
    
    # Run review
    result = await reviewer.run()
    
    # Return typed response
    return ReviewResponse(
        status="completed",
        pr=PRInfo(...),
        review=ReviewResult(...),
        metadata=ReviewMetadata(...),
    )
```

### Error Handling with Return Types
```python
from fastapi import HTTPException
from pr_agent.log import get_logger


@router.post("/review")
async def review(request: ReviewRequest) -> ReviewResponse:
    try:
        return await run_review(request.pr_url, request.config)
    except ValueError as e:
        get_logger().warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Review failed: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
```

## Dashboard API Requirements

The dashboard needs these endpoints:

### 1. POST /api/v1/dashboard/review
Trigger a review and return structured JSON (not post to PR).

**Request:**
```json
{
  "pr_url": "https://github.com/org/repo/pull/123",
  "command": "review",
  "config": { "model": "gpt-4o" },
  "context": { "coding_standards": "..." },
  "post_to_pr": false
}
```

**Response:**
```json
{
  "status": "completed",
  "pr": { "number": 123, "title": "...", "author": "..." },
  "review": { "score": 85, "summary": "...", "findings": [...] },
  "metadata": { "model": "...", "token_usage": {...}, "duration_ms": 1234 }
}
```

### 2. POST /api/v1/dashboard/describe
Generate PR description without posting.

### 3. POST /api/v1/dashboard/improve
Get code suggestions without posting.

### 4. GET /api/v1/dashboard/health
Health check endpoint.

## Guidelines

### DO
- Return structured JSON that dashboard can parse
- Support `post_to_pr: false` to disable PR comments
- Accept config overrides from request body
- Include timing and token usage in responses
- Log all requests with context
- Use `Annotated` for all parameter declarations
- Include return types on all endpoints
- Use router-level prefix/tags

### DON'T
- Modify existing webhook handlers
- Change default behavior of existing tools
- Break backwards compatibility
- Store state (dashboard owns the database)
- Use Ellipsis (`...`) for required fields
- Use `ORJSONResponse` or `UJSONResponse` (deprecated)
- Use Pydantic `RootModel`
- Mix multiple HTTP operations in one function

## Testing
Run tests with:
```bash
cd pr-agent
PYTHONPATH=. pytest tests/unittest/ -v
```
