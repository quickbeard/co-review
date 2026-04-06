"""
Dashboard Integration API for PR-Agent.

This module provides HTTP endpoints for a Next.js dashboard to orchestrate
PR-Agent as a stateless review engine. All endpoints return structured JSON
responses suitable for dashboard consumption.
"""

import copy
import time
import traceback
from typing import Annotated, Any

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette_context import context


from pr_agent.algo.pr_processing import get_pr_diff, retry_with_fallback_models
from pr_agent.algo.token_handler import TokenHandler
from pr_agent.algo.utils import ModelType, load_yaml
from pr_agent.config_loader import get_settings, global_settings
from pr_agent.git_providers import get_git_provider_with_context
from pr_agent.git_providers.git_provider import get_main_pr_language
from pr_agent.log import get_logger
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions
from pr_agent.tools.pr_description import PRDescription
from pr_agent.tools.pr_reviewer import PRReviewer


# =============================================================================
# Pydantic Models
# =============================================================================


class ConfigOverride(BaseModel):
    """Configuration overrides for the request."""
    model: str | None = Field(default=None, description="LLM model to use")
    temperature: float | None = Field(default=None, ge=0, le=2, description="Model temperature")
    extra_instructions: str | None = Field(default=None, description="Additional instructions for the AI")


class RequestContext(BaseModel):
    """Additional context for the review."""
    coding_standards: str | None = Field(default=None, description="Coding standards to enforce")
    focus_areas: list[str] | None = Field(default=None, description="Specific areas to focus on")


class DashboardRequest(BaseModel):
    """Base request model for all dashboard endpoints."""
    pr_url: str = Field(description="Full URL of the pull request")
    config: ConfigOverride | None = Field(default=None, description="Configuration overrides")
    context: RequestContext | None = Field(default=None, description="Additional review context")
    post_to_pr: bool = Field(default=False, description="Whether to post results to the PR")


class PRInfo(BaseModel):
    """Pull request metadata."""
    number: int
    title: str
    author: str
    url: str
    branch: str
    base_branch: str
    description: str | None = None


class TokenUsage(BaseModel):
    """Token usage statistics."""
    input: int = Field(default=0, description="Input tokens used")
    output: int = Field(default=0, description="Output tokens used")


class ResponseMetadata(BaseModel):
    """Metadata about the API response."""
    model: str
    token_usage: TokenUsage
    duration_ms: int
    version: str = Field(default="1.0.0")


class ReviewFinding(BaseModel):
    """A single review finding."""
    type: str = Field(description="Type of finding (e.g., 'issue', 'suggestion', 'security')")
    severity: str = Field(description="Severity level (e.g., 'critical', 'major', 'minor')")
    file: str | None = Field(default=None, description="File path if applicable")
    line: int | None = Field(default=None, description="Line number if applicable")
    description: str = Field(description="Description of the finding")
    suggestion: str | None = Field(default=None, description="Suggested fix if applicable")


class ReviewResult(BaseModel):
    """Code review result."""
    score: int | None = Field(default=None, ge=0, le=100, description="Review score (0-100)")
    summary: str = Field(description="Summary of the review")
    findings: list[ReviewFinding] = Field(default_factory=list, description="List of findings")
    estimated_effort: str | None = Field(default=None, description="Estimated review effort")
    security_concerns: str | None = Field(default=None, description="Security concerns if any")


class ReviewResponse(BaseModel):
    """Response model for the review endpoint."""
    status: str = Field(description="Status of the operation")
    pr: PRInfo
    review: ReviewResult
    metadata: ResponseMetadata


class DescriptionResult(BaseModel):
    """Generated PR description."""
    title: str = Field(description="Generated PR title")
    summary: str = Field(description="PR summary")
    type: str | None = Field(default=None, description="Type of change (feature, bugfix, etc.)")
    walkthrough: str | None = Field(default=None, description="Detailed walkthrough of changes")
    labels: list[str] = Field(default_factory=list, description="Suggested labels")


class DescriptionResponse(BaseModel):
    """Response model for the describe endpoint."""
    status: str = Field(description="Status of the operation")
    pr: PRInfo
    description: DescriptionResult
    metadata: ResponseMetadata


class CodeSuggestion(BaseModel):
    """A single code improvement suggestion."""
    file: str = Field(description="File path")
    line_start: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    existing_code: str = Field(description="Current code")
    improved_code: str = Field(description="Suggested improvement")
    label: str = Field(description="Type of improvement")
    description: str = Field(description="Description of the improvement")
    score: int | None = Field(default=None, description="Confidence score")


class ImproveResult(BaseModel):
    """Code improvement suggestions."""
    summary: str = Field(description="Summary of suggestions")
    suggestions: list[CodeSuggestion] = Field(default_factory=list, description="List of suggestions")


class ImproveResponse(BaseModel):
    """Response model for the improve endpoint."""
    status: str = Field(description="Status of the operation")
    pr: PRInfo
    improvements: ImproveResult
    metadata: ResponseMetadata


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    git_provider: str = Field(description="Configured git provider")


# =============================================================================
# Router Setup
# =============================================================================


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# =============================================================================
# Helper Functions
# =============================================================================


def _setup_request_context() -> None:
    """Initialize the request context with fresh settings."""
    try:
        context["settings"] = copy.deepcopy(global_settings)
        context["git_provider"] = {}
    except Exception:
        # Context not available (e.g., in tests), use global settings
        pass


def _apply_config_overrides(config: ConfigOverride | None, request_context: RequestContext | None) -> None:
    """Apply configuration overrides from the request."""
    settings = get_settings()

    if config:
        if config.model:
            settings.set("CONFIG.MODEL", config.model)
        if config.temperature is not None:
            settings.set("CONFIG.TEMPERATURE", config.temperature)
        if config.extra_instructions:
            # Append to existing extra instructions
            for section in ["pr_reviewer", "pr_description", "pr_code_suggestions"]:
                current = settings.get(f"{section}.extra_instructions", "")
                settings.set(f"{section}.extra_instructions", f"{current}\n{config.extra_instructions}".strip())

    if request_context:
        if request_context.coding_standards:
            for section in ["pr_reviewer", "pr_code_suggestions"]:
                current = settings.get(f"{section}.extra_instructions", "")
                standards_instruction = f"Enforce these coding standards:\n{request_context.coding_standards}"
                settings.set(f"{section}.extra_instructions", f"{current}\n{standards_instruction}".strip())

        if request_context.focus_areas:
            focus_str = ", ".join(request_context.focus_areas)
            for section in ["pr_reviewer", "pr_code_suggestions"]:
                current = settings.get(f"{section}.extra_instructions", "")
                focus_instruction = f"Focus especially on: {focus_str}"
                settings.set(f"{section}.extra_instructions", f"{current}\n{focus_instruction}".strip())


def _disable_publishing() -> None:
    """Disable publishing to PR when post_to_pr is False."""
    settings = get_settings()
    settings.set("CONFIG.PUBLISH_OUTPUT", False)
    settings.set("CONFIG.PUBLISH_OUTPUT_PROGRESS", False)


def _get_pr_info(git_provider: Any) -> PRInfo:
    """Extract PR information from git provider."""
    pr = git_provider.pr
    return PRInfo(
        number=git_provider.get_pr_id() if hasattr(git_provider, 'get_pr_id') else getattr(pr, 'number', 0),
        title=getattr(pr, 'title', ''),
        author=getattr(pr.user, 'login', '') if hasattr(pr, 'user') else '',
        url=git_provider.get_pr_url() if hasattr(git_provider, 'get_pr_url') else '',
        branch=git_provider.get_pr_branch() if hasattr(git_provider, 'get_pr_branch') else '',
        base_branch=getattr(pr.base, 'ref', '') if hasattr(pr, 'base') else '',
        description=git_provider.get_user_description() if hasattr(git_provider, 'get_user_description') else None,
    )


def _build_metadata(model: str, duration_ms: int, input_tokens: int = 0, output_tokens: int = 0) -> ResponseMetadata:
    """Build response metadata."""
    return ResponseMetadata(
        model=model,
        token_usage=TokenUsage(input=input_tokens, output=output_tokens),
        duration_ms=duration_ms,
    )


def _parse_review_findings(data: dict) -> list[ReviewFinding]:
    """Parse review findings from AI response."""
    findings = []

    # Parse key_issues_to_review
    key_issues = data.get("review", {}).get("key_issues_to_review", [])
    if isinstance(key_issues, list):
        for issue in key_issues:
            if isinstance(issue, dict):
                findings.append(ReviewFinding(
                    type="issue",
                    severity=issue.get("severity", "minor"),
                    file=issue.get("relevant_file"),
                    line=issue.get("relevant_line"),
                    description=issue.get("issue_header", "") + ": " + issue.get("issue_content", ""),
                    suggestion=issue.get("suggestion"),
                ))
            elif isinstance(issue, str):
                findings.append(ReviewFinding(
                    type="issue",
                    severity="minor",
                    description=issue,
                ))

    return findings


def _parse_code_suggestions(data: dict) -> list[CodeSuggestion]:
    """Parse code suggestions from AI response."""
    suggestions = []

    code_suggestions = data.get("code_suggestions", [])
    if isinstance(code_suggestions, list):
        for suggestion in code_suggestions:
            if isinstance(suggestion, dict):
                suggestions.append(CodeSuggestion(
                    file=suggestion.get("relevant_file", ""),
                    line_start=suggestion.get("relevant_lines_start", 0),
                    line_end=suggestion.get("relevant_lines_end", 0),
                    existing_code=suggestion.get("existing_code", ""),
                    improved_code=suggestion.get("improved_code", ""),
                    label=suggestion.get("label", "enhancement"),
                    description=suggestion.get("suggestion_content", suggestion.get("one_sentence_summary", "")),
                    score=suggestion.get("score"),
                ))

    return suggestions


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the service status, API version, and configured git provider.
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        git_provider=settings.get("CONFIG.GIT_PROVIDER", "github"),
    )


@router.post("/review")
async def review_pr(
    request: Annotated[DashboardRequest, Field(description="Review request parameters")]
) -> ReviewResponse:
    """
    Trigger a code review for a pull request.

    Analyzes the PR diff and returns structured review findings including
    issues, suggestions, security concerns, and an overall score.
    """
    start_time = time.time()

    try:
        _setup_request_context()
        _apply_config_overrides(request.config, request.context)

        if not request.post_to_pr:
            _disable_publishing()

        settings = get_settings()
        model = settings.get("CONFIG.MODEL", "gpt-4o")

        # Initialize git provider and get PR info
        git_provider = get_git_provider_with_context(request.pr_url)
        pr_info = _get_pr_info(git_provider)

        # Create reviewer instance
        reviewer = PRReviewer(request.pr_url, is_answer=False, is_auto=False, args=[])

        # Run the review
        await reviewer.run()

        # Get the prediction data
        prediction = reviewer.prediction
        if not prediction:
            raise HTTPException(status_code=500, detail="Review failed: no prediction generated")

        # Parse the prediction
        data = load_yaml(
            prediction.strip(),
            keys_fix_yaml=["ticket_compliance_check", "estimated_effort_to_review_[1-5]:",
                          "security_concerns:", "key_issues_to_review:",
                          "relevant_file:", "relevant_line:", "suggestion:"],
            first_key="review",
            last_key="security_concerns"
        )

        # Extract review data
        review_data = data.get("review", {})

        # Calculate score from estimated effort (effort 1-5 maps to score 100-20)
        effort = review_data.get("estimated_effort_to_review_[1-5]", "3")
        if isinstance(effort, str):
            try:
                effort_num = int(effort.split(",")[0])
            except (ValueError, IndexError):
                effort_num = 3
        else:
            effort_num = int(effort) if isinstance(effort, (int, float)) else 3
        score = max(20, 120 - effort_num * 20)  # effort 1->100, 2->80, 3->60, 4->40, 5->20

        findings = _parse_review_findings(data)

        duration_ms = int((time.time() - start_time) * 1000)

        return ReviewResponse(
            status="completed",
            pr=pr_info,
            review=ReviewResult(
                score=score,
                summary=review_data.get("PR Analysis", ""),
                findings=findings,
                estimated_effort=str(review_data.get("estimated_effort_to_review_[1-5]", "")),
                security_concerns=review_data.get("security_concerns"),
            ),
            metadata=_build_metadata(model, duration_ms),
        )

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Review failed: {e}", artifact={"traceback": traceback.format_exc()})
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


@router.post("/describe")
async def describe_pr(
    request: Annotated[DashboardRequest, Field(description="Description request parameters")]
) -> DescriptionResponse:
    """
    Generate a PR description.

    Analyzes the PR changes and generates a structured description including
    title, summary, type of change, walkthrough, and suggested labels.
    """
    start_time = time.time()

    try:
        _setup_request_context()
        _apply_config_overrides(request.config, request.context)

        if not request.post_to_pr:
            _disable_publishing()

        settings = get_settings()
        model = settings.get("CONFIG.MODEL", "gpt-4o")

        # Initialize git provider and get PR info
        git_provider = get_git_provider_with_context(request.pr_url)
        pr_info = _get_pr_info(git_provider)

        # Create description generator instance
        describer = PRDescription(request.pr_url, args=[])

        # Run the description generation
        await describer.run()

        # Get the prediction data
        prediction = describer.prediction
        if not prediction:
            raise HTTPException(status_code=500, detail="Description generation failed: no prediction")

        # Parse the prediction
        data = load_yaml(
            prediction.strip(),
            keys_fix_yaml=["filename:", "language:", "changes_summary:", "changes_title:",
                          "description:", "title:"],
            first_key="title",
            last_key="description"
        )

        # Extract labels if available
        labels = []
        if hasattr(describer, '_prepare_labels'):
            try:
                labels = describer._prepare_labels() or []
            except Exception:
                pass

        # Build walkthrough from file changes
        walkthrough = ""
        if "PR Description" in data:
            walkthrough = data.get("PR Description", {}).get("changes_walkthrough", "")

        duration_ms = int((time.time() - start_time) * 1000)

        return DescriptionResponse(
            status="completed",
            pr=pr_info,
            description=DescriptionResult(
                title=data.get("title", pr_info.title),
                summary=data.get("description", ""),
                type=data.get("type", None),
                walkthrough=walkthrough if walkthrough else None,
                labels=labels,
            ),
            metadata=_build_metadata(model, duration_ms),
        )

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Description generation failed: {e}", artifact={"traceback": traceback.format_exc()})
        raise HTTPException(status_code=500, detail=f"Description generation failed: {str(e)}")


@router.post("/improve")
async def improve_pr(
    request: Annotated[DashboardRequest, Field(description="Improvement request parameters")]
) -> ImproveResponse:
    """
    Get code improvement suggestions for a pull request.

    Analyzes the PR diff and returns specific code improvement suggestions
    with existing code, improved code, and explanations.
    """
    start_time = time.time()

    try:
        _setup_request_context()
        _apply_config_overrides(request.config, request.context)

        if not request.post_to_pr:
            _disable_publishing()

        settings = get_settings()
        model = settings.get("CONFIG.MODEL", "gpt-4o")

        # Initialize git provider and get PR info
        git_provider = get_git_provider_with_context(request.pr_url)
        pr_info = _get_pr_info(git_provider)

        # Create code suggestions instance
        suggester = PRCodeSuggestions(request.pr_url, cli_mode=False, args=[])

        # Run the suggestions generation
        await suggester.run()

        # Get the data
        data = getattr(suggester, 'data', {})
        if not data:
            raise HTTPException(status_code=500, detail="Suggestions generation failed: no data")

        suggestions = _parse_code_suggestions(data)

        # Build summary
        num_suggestions = len(suggestions)
        summary = f"Found {num_suggestions} code improvement suggestion{'s' if num_suggestions != 1 else ''}"

        duration_ms = int((time.time() - start_time) * 1000)

        return ImproveResponse(
            status="completed",
            pr=pr_info,
            improvements=ImproveResult(
                summary=summary,
                suggestions=suggestions,
            ),
            metadata=_build_metadata(model, duration_ms),
        )

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Suggestions generation failed: {e}", artifact={"traceback": traceback.format_exc()})
        raise HTTPException(status_code=500, detail=f"Suggestions generation failed: {str(e)}")


# =============================================================================
# Standalone Server
# =============================================================================


def create_app() -> FastAPI:
    """
    Create a FastAPI application with the dashboard router.

    Returns:
        FastAPI: Configured FastAPI application instance.

    Usage:
        # Import and include in existing app:
        from pr_agent.servers.dashboard_api import router
        app.include_router(router)

        # Or run standalone:
        from pr_agent.servers.dashboard_api import create_app
        app = create_app()
    """
    from starlette.middleware import Middleware
    from starlette_context.middleware import RawContextMiddleware

    from pr_agent.log import LoggingFormat, setup_logger

    setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "DEBUG"))

    middleware = [Middleware(RawContextMiddleware)]
    app = FastAPI(
        title="PR-Agent Dashboard API",
        description="HTTP API for dashboard integration with PR-Agent",
        version="1.0.0",
        middleware=middleware,
    )
    app.include_router(router)

    return app


def start() -> None:
    """Start the dashboard API server."""
    import os
    import uvicorn

    app = create_app()
    host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("DASHBOARD_PORT", "3001"))

    uvicorn.run(app, host=host, port=port)


# Module-level app instance for gunicorn
app = create_app()


if __name__ == "__main__":
    start()
