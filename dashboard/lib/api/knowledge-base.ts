// Knowledge-base API client.
// Manages the `[knowledge_base]` section of configuration.toml via the dashboard.
// Shape mirrors pr_agent.servers.api.KnowledgeBaseConfig.
// Follows the ApiResponse<T> pattern from token-limits.ts / automation.ts.

const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

// Template rules surfaced by the UI when the user toggles off
// `explicit_learn_enabled`. The backend seeds the same list if this reaches
// the server with an empty rules array, so this is purely an ergonomic
// client-side prefill - it guarantees the user sees concrete examples they
// can then edit or delete, instead of staring at an empty box.
export const KNOWLEDGE_BASE_TEMPLATE_RULES: readonly string[] = [
  "we prefer",
  "in this project",
  "in this repo",
  "we always",
  "we never",
  "our standard",
  "our convention",
  "please avoid",
  "do not suggest",
  "should use",
  "shouldn't use",
];

export interface KnowledgeBaseConfig {
  enabled: boolean;
  explicit_learn_enabled: boolean;
  learn_command: string;
  extraction_rules: string[];
  apply_to_review: boolean;
  max_retrieved_learnings: number;
  max_summary_chars: number;
  duplicate_threshold: number;
  capture_from_pr_comments: boolean;
  require_agent_mention: boolean;
}

export type KnowledgeBaseConfigUpdate = Partial<KnowledgeBaseConfig>;

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
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

export async function getKnowledgeBaseConfig(): Promise<
  ApiResponse<KnowledgeBaseConfig>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-base`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail ||
          error.message ||
          "Failed to fetch knowledge base config",
      };
    }

    const data: KnowledgeBaseConfig = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch knowledge base config:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function updateKnowledgeBaseConfig(
  update: KnowledgeBaseConfigUpdate,
): Promise<ApiResponse<KnowledgeBaseConfig>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-base`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail ||
          error.message ||
          "Failed to update knowledge base config",
      };
    }

    const data: KnowledgeBaseConfig = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to update knowledge base config:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function reloadKnowledgeBaseConfig(): Promise<ApiResponse<null>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/knowledge-base/reload`,
      { method: "POST" },
    );

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail ||
          error.message ||
          "Failed to reload knowledge base config",
      };
    }

    return { success: true, data: null };
  } catch (error) {
    console.error("Failed to reload knowledge base config:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
