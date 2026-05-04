// Webhook registry API client (P1).
// CRUD for per-repository webhook registrations plus provider-side actions
// (register / unregister / test / deliveries). Mirrors the ApiResponse<T>
// envelope convention used elsewhere in lib/api.

const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

export type WebhookRegistrationStatus =
  | "draft"
  | "registered"
  | "failed"
  | "deleted";

export interface WebhookRegistration {
  id: number;
  git_provider_id: number;
  repo: string;
  target_url: string;
  events: string[];
  active: boolean;
  content_type: string;
  insecure_ssl: boolean;
  status: WebhookRegistrationStatus;
  external_id: string | null;
  has_secret: boolean;
  last_delivery_at: string | null;
  last_status_code: number | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebhookRegistrationCreateInput {
  git_provider_id: number;
  repo: string;
  target_url: string;
  events?: string[] | null;
  active?: boolean;
  content_type?: string;
  insecure_ssl?: boolean;
  secret?: string | null;
}

export type WebhookRegistrationUpdateInput = Partial<
  Omit<WebhookRegistrationCreateInput, "git_provider_id">
>;

export interface WebhookDelivery {
  id: string;
  delivered_at: string | null;
  status: string | null;
  status_code: number | null;
  event: string | null;
  action: string | null;
  duration_ms: number | null;
  redelivery: boolean;
  url: string | null;
}

export interface WebhookEndpointInfo {
  provider_type: string;
  path: string;
  default_events: string[];
  note: string | null;
}

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

// --- CRUD --------------------------------------------------------------

export async function getWebhooks(filters?: {
  gitProviderId?: number;
  repo?: string;
}): Promise<ApiResponse<WebhookRegistration[]>> {
  try {
    const params = new URLSearchParams();
    if (filters?.gitProviderId !== undefined) {
      params.set("git_provider_id", String(filters.gitProviderId));
    }
    if (filters?.repo) {
      params.set("repo", filters.repo);
    }
    const qs = params.toString();
    const response = await fetch(
      `${API_BASE_URL}/api/webhooks${qs ? `?${qs}` : ""}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      },
    );
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to fetch webhooks",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to fetch webhooks:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function getWebhook(
  id: number | string,
): Promise<ApiResponse<WebhookRegistration>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/webhooks/${id}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Webhook not found",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to fetch webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function createWebhook(
  input: WebhookRegistrationCreateInput,
): Promise<ApiResponse<WebhookRegistration>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/webhooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to create webhook",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to create webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function updateWebhook(
  id: number | string,
  input: WebhookRegistrationUpdateInput,
): Promise<ApiResponse<WebhookRegistration>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/webhooks/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to update webhook",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to update webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function deleteWebhook(
  id: number | string,
  alsoUnregister: boolean = true,
): Promise<ApiResponse<null>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/webhooks/${id}?also_unregister=${alsoUnregister}`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      },
    );
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to delete webhook",
      };
    }
    return { success: true, data: null };
  } catch (error) {
    console.error("Failed to delete webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

// --- Provider actions --------------------------------------------------

export async function registerWebhook(
  id: number | string,
): Promise<ApiResponse<WebhookRegistration>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/webhooks/${id}/register`,
      { method: "POST", headers: { "Content-Type": "application/json" } },
    );
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to register webhook",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to register webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function unregisterWebhook(
  id: number | string,
): Promise<ApiResponse<WebhookRegistration>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/webhooks/${id}/unregister`,
      { method: "POST", headers: { "Content-Type": "application/json" } },
    );
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to unregister webhook",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to unregister webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function testWebhook(
  id: number | string,
): Promise<
  ApiResponse<{ message: string | null; status_code: number | null }>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/webhooks/${id}/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to send test delivery",
      };
    }
    const body = await response.json();
    return {
      success: true,
      data: {
        message: body.message ?? null,
        status_code: body.status_code ?? null,
      },
    };
  } catch (error) {
    console.error("Failed to test webhook:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function getWebhookDeliveries(
  id: number | string,
  limit: number = 30,
): Promise<ApiResponse<WebhookDelivery[]>> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/webhooks/${id}/deliveries?limit=${limit}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      },
    );
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to fetch deliveries",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to fetch webhook deliveries:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}

export async function getWebhookEndpoints(): Promise<
  ApiResponse<WebhookEndpointInfo[]>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/webhooks/endpoints`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      const err = await parseErrorResponse(response);
      return {
        success: false,
        error: err.detail || err.message || "Failed to fetch endpoints",
      };
    }
    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Failed to fetch webhook endpoints:", error);
    return { success: false, error: "Failed to connect to PR-Agent API" };
  }
}
