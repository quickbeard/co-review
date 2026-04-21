import type { ApiResponse } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

export interface Learning {
  id: string | null;
  repo: string | null;
  text: string;
  createdAt: string | null;
  metadata: Record<string, unknown>;
}

export interface LearningsResponse {
  enabled: boolean;
  total: number;
  items: Learning[];
  repos: string[];
}

interface LearningApiItem {
  id: string | null;
  repo: string | null;
  text: string;
  created_at: string | null;
  metadata: Record<string, unknown>;
}

interface LearningsApiResponse {
  enabled: boolean;
  total: number;
  items: LearningApiItem[];
  repos: string[];
}

function transformItem(item: LearningApiItem): Learning {
  return {
    id: item.id,
    repo: item.repo,
    text: item.text,
    createdAt: item.created_at,
    metadata: item.metadata ?? {},
  };
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

export async function getLearnings(options?: {
  repo?: string;
  limit?: number;
}): Promise<ApiResponse<LearningsResponse>> {
  try {
    const params = new URLSearchParams();
    if (options?.repo) params.set("repo", options.repo);
    if (options?.limit) params.set("limit", String(options.limit));
    const query = params.toString();

    const response = await fetch(
      `${API_BASE_URL}/api/learnings${query ? `?${query}` : ""}`,
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
        error: error.detail || error.message || "Failed to fetch learnings",
      };
    }

    const data: LearningsApiResponse = await response.json();
    return {
      success: true,
      data: {
        enabled: data.enabled,
        total: data.total,
        items: (data.items ?? []).map(transformItem),
        repos: data.repos ?? [],
      },
    };
  } catch (error) {
    console.error("Failed to fetch learnings:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function deleteLearning(
  id: string,
): Promise<ApiResponse<void>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/learnings/${encodeURIComponent(id)}`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      },
    );

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to delete learning",
      };
    }

    return { success: true };
  } catch (error) {
    console.error("Failed to delete learning:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
