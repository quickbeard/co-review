// Token Limits API client
// Follows the pattern in llm-providers.ts

// PR-Agent API base URL - configured via environment variable
const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

/**
 * Token limits configuration
 */
export interface TokenLimits {
  max_description_tokens: number;
  max_commits_tokens: number;
  max_model_tokens: number;
  custom_model_max_tokens: number;
}

/**
 * API response wrapper
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Parse error response from API
 */
async function parseErrorResponse(
  response: Response,
): Promise<{ message?: string; detail?: string }> {
  try {
    return await response.json();
  } catch {
    return { message: `HTTP ${response.status}: ${response.statusText}` };
  }
}

/**
 * Fetch current token limits configuration
 */
export async function getTokenLimits(): Promise<ApiResponse<TokenLimits>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/token-limits`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to fetch token limits",
      };
    }

    const data: TokenLimits = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch token limits:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Update token limits configuration
 */
export async function updateTokenLimits(
  limits: Partial<TokenLimits>,
): Promise<ApiResponse<TokenLimits>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/token-limits`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(limits),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to update token limits",
      };
    }

    const data: TokenLimits = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to update token limits:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Fetch default token limits values
 */
export async function getDefaultTokenLimits(): Promise<
  ApiResponse<TokenLimits>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/token-limits/defaults`, {
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
          "Failed to fetch default token limits",
      };
    }

    const data: TokenLimits = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch default token limits:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Reset token limits to default values
 */
export async function resetTokenLimits(): Promise<ApiResponse<TokenLimits>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/token-limits/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to reset token limits",
      };
    }

    const data: TokenLimits = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to reset token limits:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
