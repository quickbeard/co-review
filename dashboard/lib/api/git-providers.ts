import type {
  GitProvider,
  GitProviderApiResponse,
  CreateGitProviderInput,
  UpdateGitProviderInput,
  DevLakeIntegration,
  DevLakeIntegrationApiResponse,
  DevLakeValidateResponse,
  DevLakeSyncAcceptedResponse,
  DevLakeSyncJobStatusResponse,
  DevLakeRemoteScopesResponse,
  UpdateDevLakeIntegrationInput,
  ApiResponse,
} from "./types";
import {
  transformApiResponseToProvider,
  transformDevLakeApiResponse,
  transformCreateInputToApiRequest,
  transformUpdateDevLakeInputToApiRequest,
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
    const response = await fetch(`${API_BASE_URL}/api/git-providers`, {
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
    const response = await fetch(`${API_BASE_URL}/api/git-providers/${id}`, {
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
  options?: { autoSyncOnCreate?: boolean; devlakeProjectName?: string },
): Promise<ApiResponse<GitProvider>> {
  try {
    const apiRequest = transformCreateInputToApiRequest(input);
    const params = new URLSearchParams();
    if (options?.autoSyncOnCreate === true) {
      params.set("auto_sync_on_create", "true");
      const projectName = options?.devlakeProjectName?.trim();
      if (projectName) params.set("devlake_project_name", projectName);
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    const response = await fetch(`${API_BASE_URL}/api/git-providers${query}`, {
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
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${input.id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(apiRequest),
      },
    );

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
    const response = await fetch(`${API_BASE_URL}/api/git-providers/${id}`, {
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
    const response = await fetch(`${API_BASE_URL}/api/git-providers/${id}`, {
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

export async function getDevLakeIntegration(
  providerId: number | string,
): Promise<ApiResponse<DevLakeIntegration>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${providerId}/devlake`,
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
        error: error.detail || error.message || "Failed to load DevLake config",
      };
    }
    const data: DevLakeIntegrationApiResponse = await response.json();
    return { success: true, data: transformDevLakeApiResponse(data) };
  } catch (error) {
    console.error("Failed to get DevLake integration:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function updateDevLakeIntegration(
  providerId: number | string,
  input: UpdateDevLakeIntegrationInput,
): Promise<ApiResponse<DevLakeIntegration>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${providerId}/devlake`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(transformUpdateDevLakeInputToApiRequest(input)),
      },
    );
    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to save DevLake config",
      };
    }
    const data: DevLakeIntegrationApiResponse = await response.json();
    return { success: true, data: transformDevLakeApiResponse(data) };
  } catch (error) {
    console.error("Failed to update DevLake integration:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function validateDevLakeIntegration(
  providerId: number | string,
): Promise<ApiResponse<DevLakeValidateResponse>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${providerId}/devlake/validate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      },
    );
    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Validation failed",
      };
    }
    const data: DevLakeValidateResponse = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to validate DevLake integration:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function listDevLakeRemoteScopes(
  providerId: number | string,
): Promise<ApiResponse<DevLakeRemoteScopesResponse>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${providerId}/devlake/remote-scopes`,
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
        error: error.detail || error.message || "Failed to load remote scopes",
      };
    }
    const data: DevLakeRemoteScopesResponse = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to list DevLake remote scopes:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function enqueueDevLakeSync(
  providerId: number | string,
  input?: { fullSync?: boolean; skipCollectors?: boolean },
): Promise<ApiResponse<DevLakeSyncAcceptedResponse>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${providerId}/devlake/sync`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_sync: input?.fullSync ?? false,
          skip_collectors: input?.skipCollectors ?? false,
        }),
      },
    );
    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to queue DevLake sync",
      };
    }
    const data: DevLakeSyncAcceptedResponse = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to enqueue DevLake sync:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function getDevLakeSyncJobStatus(
  providerId: number | string,
  jobId: string,
): Promise<ApiResponse<DevLakeSyncJobStatusResponse>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/git-providers/${providerId}/devlake/sync-jobs/${jobId}`,
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
        error: error.detail || error.message || "Failed to load sync job status",
      };
    }
    const data: DevLakeSyncJobStatusResponse = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to get DevLake sync job status:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
