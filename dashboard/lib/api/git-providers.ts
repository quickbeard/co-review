import type {
  GitProvider,
  CreateGitProviderInput,
  UpdateGitProviderInput,
  ApiResponse,
} from "./types";

// PR-Agent API base URL - configured via environment variable
const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

/**
 * Fetch all git providers
 */
export async function getGitProviders(): Promise<ApiResponse<GitProvider[]>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || "Failed to fetch providers",
      };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch git providers:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Fetch a single git provider by ID
 */
export async function getGitProvider(
  id: string,
): Promise<ApiResponse<GitProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${id}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.message || "Provider not found" };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch git provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Create a new git provider
 */
export async function createGitProvider(
  input: CreateGitProviderInput,
): Promise<ApiResponse<GitProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || "Failed to create provider",
        fieldErrors: error.fieldErrors,
      };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to create git provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Update an existing git provider
 */
export async function updateGitProvider(
  input: UpdateGitProviderInput,
): Promise<ApiResponse<GitProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${input.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || "Failed to update provider",
        fieldErrors: error.fieldErrors,
      };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to update git provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Delete a git provider
 */
export async function deleteGitProvider(
  id: string,
): Promise<ApiResponse<void>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || "Failed to delete provider",
      };
    }

    return { success: true };
  } catch (error) {
    console.error("Failed to delete git provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Toggle git provider active status
 */
export async function toggleGitProviderStatus(
  id: string,
  isActive: boolean,
): Promise<ApiResponse<GitProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isActive }),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || "Failed to update status",
      };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to toggle git provider status:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
