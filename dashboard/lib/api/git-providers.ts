import type {
  GitProvider,
  GitProviderApiResponse,
  CreateGitProviderInput,
  UpdateGitProviderInput,
  ApiResponse,
} from "./types";
import {
  transformApiResponseToProvider,
  transformCreateInputToApiRequest,
  transformUpdateInputToApiRequest,
} from "./types";

// PR-Agent API base URL - configured via environment variable
const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

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
 * Fetch all git providers
 */
export async function getGitProviders(): Promise<ApiResponse<GitProvider[]>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to fetch providers",
      };
    }

    const data: GitProviderApiResponse[] = await response.json();
    return {
      success: true,
      data: data.map(transformApiResponseToProvider),
    };
  } catch (error) {
    console.error("Failed to fetch git providers:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Fetch a single git provider by ID
 */
export async function getGitProvider(
  id: number | string,
): Promise<ApiResponse<GitProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${id}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Provider not found",
      };
    }

    const data: GitProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
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
    const apiRequest = transformCreateInputToApiRequest(input);
    const response = await fetch(`${API_BASE_URL}/api/providers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(apiRequest),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to create provider",
      };
    }

    const data: GitProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
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
    const apiRequest = transformUpdateInputToApiRequest(input);
    const response = await fetch(`${API_BASE_URL}/api/providers/${input.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(apiRequest),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to update provider",
      };
    }

    const data: GitProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to update git provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Delete a git provider
 */
export async function deleteGitProvider(
  id: number | string,
): Promise<ApiResponse<void>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to delete provider",
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
  id: number | string,
  isActive: boolean,
): Promise<ApiResponse<GitProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to update status",
      };
    }

    const data: GitProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to toggle git provider status:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
