import type {
  LLMProvider,
  LLMProviderApiResponse,
  CreateLLMProviderInput,
  UpdateLLMProviderInput,
  ApiResponse,
  LLMProviderType,
} from "./llm-provider-types";
import {
  transformApiResponseToProvider,
  transformCreateInputToApiRequest,
  transformUpdateInputToApiRequest,
} from "./llm-provider-types";
import { normalizeApiBaseUrl } from "@/lib/validators";

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
 * Fetch all LLM providers
 */
export async function getLLMProviders(): Promise<ApiResponse<LLMProvider[]>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm-providers`, {
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

    const data: LLMProviderApiResponse[] = await response.json();
    return {
      success: true,
      data: data.map(transformApiResponseToProvider),
    };
  } catch (error) {
    console.error("Failed to fetch LLM providers:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Fetch supported LLM provider types
 */
export async function getLLMProviderTypes(): Promise<
  ApiResponse<LLMProviderType[]>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm-providers/types`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error:
          error.detail || error.message || "Failed to fetch provider types",
      };
    }

    const data: LLMProviderType[] = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error("Failed to fetch LLM provider types:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Fetch a single LLM provider by ID
 */
export async function getLLMProvider(
  id: number | string,
): Promise<ApiResponse<LLMProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm-providers/${id}`, {
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

    const data: LLMProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to fetch LLM provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Create a new LLM provider
 */
export async function createLLMProvider(
  input: CreateLLMProviderInput,
): Promise<ApiResponse<LLMProvider>> {
  try {
    const apiRequest = transformCreateInputToApiRequest(input);
    const response = await fetch(`${API_BASE_URL}/api/llm-providers`, {
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

    const data: LLMProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to create LLM provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Update an existing LLM provider
 */
export async function updateLLMProvider(
  input: UpdateLLMProviderInput,
): Promise<ApiResponse<LLMProvider>> {
  try {
    const apiRequest = transformUpdateInputToApiRequest(input);
    const response = await fetch(
      `${API_BASE_URL}/api/llm-providers/${input.id}`,
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

    const data: LLMProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to update LLM provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Delete an LLM provider
 */
export async function deleteLLMProvider(
  id: number | string,
): Promise<ApiResponse<void>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm-providers/${id}`, {
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
    console.error("Failed to delete LLM provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Toggle LLM provider active status
 */
export async function toggleLLMProviderStatus(
  id: number | string,
  isActive: boolean,
): Promise<ApiResponse<LLMProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm-providers/${id}`, {
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

    const data: LLMProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to toggle LLM provider status:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Set an LLM provider as the default
 */
export async function setDefaultLLMProvider(
  id: number | string,
): Promise<ApiResponse<LLMProvider>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm-providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_default: true }),
    });

    if (!response.ok) {
      const error = await parseErrorResponse(response);
      return {
        success: false,
        error: error.detail || error.message || "Failed to set as default",
      };
    }

    const data: LLMProviderApiResponse = await response.json();
    return { success: true, data: transformApiResponseToProvider(data) };
  } catch (error) {
    console.error("Failed to set default LLM provider:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

/**
 * Provider types that support fetching models via API
 */
export const MODEL_FETCHABLE_PROVIDERS = ["openai"] as const;

/**
 * Default API base URL fallback
 */
export const DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1";

/**
 * Default model for specific API bases
 */
export const DEFAULT_MODELS_BY_API_BASE: Record<string, string> = {
  "https://netmind.viettel.vn/gateway/v1": "MiniMax/MiniMax-M2.5",
};

/**
 * Fetch available models from an LLM provider
 * This is called client-side to avoid CORS issues
 */
export async function fetchProviderModels(
  providerType: string,
  apiKey: string,
  apiBase?: string,
): Promise<ApiResponse<string[]>> {
  // Normalize and fallback the URL
  const normalizedBase = normalizeApiBaseUrl(
    apiBase || "",
    DEFAULT_OPENAI_API_BASE,
  );

  if (!normalizedBase) {
    return {
      success: false,
      error: "API base URL is required for this provider",
    };
  }

  const modelsUrl = `${normalizedBase}/models`;

  let response: Response;
  try {
    response = await fetch(modelsUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
    });
  } catch {
    // Network error, CORS issue, or invalid URL - don't log to console
    return {
      success: false,
      error:
        "Failed to fetch models. Please check your API Base URL - it should include the full path (e.g., https://example.com/gateway/v1).",
    };
  }

  if (!response.ok) {
    // Special message for 401 errors
    if (response.status === 401) {
      return {
        success: false,
        error:
          "Failed to fetch models, you might want to check your API Key or API Base URL.",
      };
    }
    // Special message for 404 errors
    if (response.status === 404) {
      return {
        success: false,
        error:
          "Models endpoint not found. Please check your API Base URL - it should include the full path (e.g., https://example.com/gateway/v1).",
      };
    }

    let errorMessage = `Failed to fetch models (${response.status})`;
    try {
      const error = await parseErrorResponse(response);
      errorMessage = error.detail || error.message || errorMessage;
    } catch {
      // Ignore parse errors
    }

    return {
      success: false,
      error: errorMessage,
    };
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    return {
      success: false,
      error: "Failed to parse models response",
    };
  }

  // Handle different response formats
  let models: string[] = [];

  if (Array.isArray(data)) {
    // Ollama format: [{ name: "model", ... }]
    models = data
      .map((m: { name?: string; id?: string }) => m.name || m.id || "")
      .filter(Boolean);
  } else if (
    data &&
    typeof data === "object" &&
    "data" in data &&
    Array.isArray((data as { data: unknown }).data)
  ) {
    // OpenAI format: { data: [{ id: "model", ... }] }
    models = (data as { data: { id: string }[] }).data
      .map((m) => m.id)
      .filter(Boolean);
  } else if (
    data &&
    typeof data === "object" &&
    "models" in data &&
    Array.isArray((data as { models: unknown }).models)
  ) {
    // Alternative format: { models: ["model1", "model2"] }
    models = (data as { models: string[] }).models;
  }

  // Deduplicate and sort models alphabetically
  models = [...new Set(models)].sort((a, b) => a.localeCompare(b));

  return { success: true, data: models };
}
