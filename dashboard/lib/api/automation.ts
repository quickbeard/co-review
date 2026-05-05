// Automation API client.
// Manages per-provider auto-review behavior (pr_commands, push_commands, toggles)
// that previously lived in .pr_agent.toml.
// Follows the ApiResponse<T> pattern from token-limits.ts.

const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

export type AutomationProviderKey =
  | "github_app"
  | "gitlab"
  | "bitbucket_app"
  | "azure_devops"
  | "gitea";

export interface ProviderAutomationConfig {
  pr_commands: string[];
  push_commands: string[];
  handle_push_trigger: boolean;
  handle_pr_actions?: string[] | null;
  feedback_on_draft_pr?: boolean | null;
  disable_auto_feedback?: boolean | null;
}

export interface AutomationConfig {
  disable_auto_feedback: boolean;
  github_app: ProviderAutomationConfig;
  gitlab: ProviderAutomationConfig;
  bitbucket_app: ProviderAutomationConfig;
  azure_devops: ProviderAutomationConfig;
  gitea: ProviderAutomationConfig;
}

export type AutomationConfigUpdate = Partial<
  Pick<AutomationConfig, "disable_auto_feedback">
> &
  Partial<Record<AutomationProviderKey, Partial<ProviderAutomationConfig>>>;

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

export async function getAutomationConfig(): Promise<
  ApiResponse<AutomationConfig>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/automation`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail || error.message || "Failed to fetch automation config",
      };
    }

    const data: AutomationConfig = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch automation config:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function updateAutomationConfig(
  update: AutomationConfigUpdate,
): Promise<ApiResponse<AutomationConfig>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/automation`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail || error.message || "Failed to update automation config",
      };
    }

    const data: AutomationConfig = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to update automation config:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function reloadAutomationConfig(): Promise<ApiResponse<null>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/automation/reload`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail || error.message || "Failed to reload automation config",
      };
    }

    return { success: true, data: null };
  } catch (error) {
    console.error("Failed to reload automation config:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
