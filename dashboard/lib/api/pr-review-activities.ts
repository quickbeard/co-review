import type { ApiResponse } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

export type PRReviewTriggeredBy =
  | "manual"
  | "automatic"
  | "cli"
  | "unknown";

export interface PRReviewActivity {
  id: number;
  providerType: string | null;
  repo: string | null;
  prNumber: number | null;
  prUrl: string | null;
  tool: string;
  triggeredBy: PRReviewTriggeredBy;
  success: boolean;
  durationMs: number | null;
  createdAt: string;
}

export interface PRReviewActivityStats {
  totalInvocations: number;
  successfulInvocations: number;
  uniquePrs: number;
  uniqueRepos: number;
  /** Distinct PRs that received at least one review-class tool (review/improve/describe). */
  reviewToolsUniquePrs: number;
  byTool: Record<string, number>;
  byTrigger: Record<string, number>;
}

interface PRReviewActivityApi {
  id: number;
  provider_type: string | null;
  repo: string | null;
  pr_number: number | null;
  pr_url: string | null;
  tool: string;
  triggered_by: PRReviewTriggeredBy;
  success: boolean;
  duration_ms: number | null;
  created_at: string;
}

interface PRReviewActivityStatsApi {
  total_invocations: number;
  successful_invocations: number;
  unique_prs: number;
  unique_repos: number;
  review_tools_unique_prs: number;
  by_tool: Record<string, number>;
  by_trigger: Record<string, number>;
}

interface PRReviewActivitiesListApi {
  total: number;
  items: PRReviewActivityApi[];
}

async function parseErrorResponse(
  response: Response,
): Promise<{ message?: string; detail?: string }> {
  try {
    return await response.json();
  } catch {
    return { message: `HTTP ${response.status}: ${response.statusText}` };
  }
}

function transformStats(api: PRReviewActivityStatsApi): PRReviewActivityStats {
  return {
    totalInvocations: api.total_invocations ?? 0,
    successfulInvocations: api.successful_invocations ?? 0,
    uniquePrs: api.unique_prs ?? 0,
    uniqueRepos: api.unique_repos ?? 0,
    reviewToolsUniquePrs: api.review_tools_unique_prs ?? 0,
    byTool: api.by_tool ?? {},
    byTrigger: api.by_trigger ?? {},
  };
}

function transformActivity(api: PRReviewActivityApi): PRReviewActivity {
  return {
    id: api.id,
    providerType: api.provider_type,
    repo: api.repo,
    prNumber: api.pr_number,
    prUrl: api.pr_url,
    tool: api.tool,
    triggeredBy: api.triggered_by,
    success: api.success,
    durationMs: api.duration_ms,
    createdAt: api.created_at,
  };
}

export async function getPRReviewActivityStats(options?: {
  repo?: string;
}): Promise<ApiResponse<PRReviewActivityStats>> {
  try {
    const params = new URLSearchParams();
    if (options?.repo) params.set("repo", options.repo);
    const query = params.toString();

    const response = await fetch(
      `${API_BASE_URL}/api/pr-review-activities/stats${query ? `?${query}` : ""}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail ||
          error.message ||
          "Failed to fetch PR review activity stats",
      };
    }

    const data: PRReviewActivityStatsApi = await response.json();
    return { success: true, data: transformStats(data) };
  } catch (error) {
    console.error("Failed to fetch PR review activity stats:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function getPRReviewActivities(options?: {
  repo?: string;
  tool?: string;
  limit?: number;
}): Promise<ApiResponse<{ total: number; items: PRReviewActivity[] }>> {
  try {
    const params = new URLSearchParams();
    if (options?.repo) params.set("repo", options.repo);
    if (options?.tool) params.set("tool", options.tool);
    if (options?.limit) params.set("limit", String(options.limit));
    const query = params.toString();

    const response = await fetch(
      `${API_BASE_URL}/api/pr-review-activities${query ? `?${query}` : ""}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail ||
          error.message ||
          "Failed to fetch PR review activities",
      };
    }

    const data: PRReviewActivitiesListApi = await response.json();
    return {
      success: true,
      data: {
        total: data.total ?? 0,
        items: (data.items ?? []).map(transformActivity),
      },
    };
  } catch (error) {
    console.error("Failed to fetch PR review activities:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
