// Git Provider Types
// These match the PR-Agent API schema

export type GitProviderType =
  | "github"
  | "gitlab"
  | "bitbucket"
  | "azure_devops"
  | "gitea"
  | "gerrit";

export type GitHubDeploymentType = "user" | "app";

// Frontend model (camelCase)
export interface GitProvider {
  id: number;
  type: GitProviderType;
  name: string;
  baseUrl: string | null;
  webhookSecret: string | null;
  isActive: boolean;
  deploymentType: GitHubDeploymentType | null; // Only for GitHub
  createdAt: string;
  updatedAt: string;
}

// API response model (snake_case) - as returned by PR-Agent API
export interface GitProviderApiResponse {
  id: number;
  type: GitProviderType;
  name: string;
  base_url: string | null;
  webhook_secret: string | null;
  is_active: boolean;
  deployment_type: GitHubDeploymentType | null;
  created_at: string;
  updated_at: string;
}

// API request model for creating (snake_case)
export interface CreateGitProviderApiRequest {
  type: GitProviderType;
  name: string;
  base_url?: string | null;
  access_token?: string;
  deployment_type?: GitHubDeploymentType;
  app_id?: string;
  private_key?: string;
  webhook_secret?: string;
}

// Frontend input for creating
export interface CreateGitProviderInput {
  type: GitProviderType;
  name: string;
  baseUrl?: string;
  // For user deployment (GitHub) or other providers
  accessToken?: string;
  // For GitHub App deployment
  deploymentType?: GitHubDeploymentType;
  appId?: string;
  privateKey?: string;
  webhookSecret?: string;
}

// API request model for updating (snake_case)
export interface UpdateGitProviderApiRequest {
  name?: string;
  base_url?: string | null;
  access_token?: string;
  deployment_type?: GitHubDeploymentType;
  app_id?: string;
  private_key?: string;
  webhook_secret?: string;
}

// Frontend input for updating
export interface UpdateGitProviderInput {
  id: number;
  name?: string;
  baseUrl?: string;
  accessToken?: string;
  deploymentType?: GitHubDeploymentType;
  appId?: string;
  privateKey?: string;
  webhookSecret?: string;
}

// API request for toggling status (snake_case)
export interface ToggleStatusApiRequest {
  is_active: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  fieldErrors?: Record<string, string>;
}

// DevLake integration types
export interface DevLakeIntegration {
  id: number;
  gitProviderId: number;
  enabled: boolean;
  pluginName: string | null;
  connectionId: number | null;
  blueprintId: number | null;
  projectName: string | null;
  selectedScopes: Record<string, unknown>[];
  lastPipelineId: number | null;
  lastSyncStatus: string | null;
  lastSyncError: string | null;
  lastSyncedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DevLakeIntegrationApiResponse {
  id: number;
  git_provider_id: number;
  enabled: boolean;
  plugin_name: string | null;
  connection_id: number | null;
  blueprint_id: number | null;
  project_name: string | null;
  selected_scopes: Record<string, unknown>[];
  last_pipeline_id: number | null;
  last_sync_status: string | null;
  last_sync_error: string | null;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateDevLakeIntegrationInput {
  enabled?: boolean;
  projectName?: string;
  selectedScopes?: Record<string, unknown>[];
}

export interface UpdateDevLakeIntegrationApiRequest {
  enabled?: boolean;
  project_name?: string;
  selected_scopes?: Record<string, unknown>[];
}

export interface DevLakeValidateResponse {
  success: boolean;
  plugin_name: string;
  connection_id: number;
  remote_scope_count: number;
  message: string;
}

export interface DevLakeSyncAcceptedResponse {
  job_id: string;
  status: string;
}

export interface DevLakeSyncJobStatusResponse {
  job_id: string;
  status: string;
  provider_id: number;
  started_at: string;
  finished_at: string | null;
  result: {
    status: string;
    plugin_name: string;
    connection_id: number;
    blueprint_id: number;
    pipeline_id: number | null;
  } | null;
  error: string | null;
}

// Transform functions
export function transformApiResponseToProvider(
  apiResponse: GitProviderApiResponse,
): GitProvider {
  return {
    id: apiResponse.id,
    type: apiResponse.type,
    name: apiResponse.name,
    baseUrl: apiResponse.base_url,
    webhookSecret: apiResponse.webhook_secret,
    isActive: apiResponse.is_active,
    deploymentType: apiResponse.deployment_type,
    createdAt: apiResponse.created_at,
    updatedAt: apiResponse.updated_at,
  };
}

export function transformCreateInputToApiRequest(
  input: CreateGitProviderInput,
): CreateGitProviderApiRequest {
  return {
    type: input.type,
    name: input.name,
    base_url: input.baseUrl || null,
    access_token: input.accessToken,
    deployment_type: input.deploymentType,
    app_id: input.appId,
    private_key: input.privateKey,
    webhook_secret: input.webhookSecret,
  };
}

export function transformUpdateInputToApiRequest(
  input: UpdateGitProviderInput,
): UpdateGitProviderApiRequest {
  return {
    name: input.name,
    base_url: input.baseUrl,
    access_token: input.accessToken,
    deployment_type: input.deploymentType,
    app_id: input.appId,
    private_key: input.privateKey,
    webhook_secret: input.webhookSecret,
  };
}

export function transformDevLakeApiResponse(
  apiResponse: DevLakeIntegrationApiResponse,
): DevLakeIntegration {
  return {
    id: apiResponse.id,
    gitProviderId: apiResponse.git_provider_id,
    enabled: apiResponse.enabled,
    pluginName: apiResponse.plugin_name,
    connectionId: apiResponse.connection_id,
    blueprintId: apiResponse.blueprint_id,
    projectName: apiResponse.project_name,
    selectedScopes: apiResponse.selected_scopes ?? [],
    lastPipelineId: apiResponse.last_pipeline_id,
    lastSyncStatus: apiResponse.last_sync_status,
    lastSyncError: apiResponse.last_sync_error,
    lastSyncedAt: apiResponse.last_synced_at,
    createdAt: apiResponse.created_at,
    updatedAt: apiResponse.updated_at,
  };
}

export function transformUpdateDevLakeInputToApiRequest(
  input: UpdateDevLakeIntegrationInput,
): UpdateDevLakeIntegrationApiRequest {
  return {
    enabled: input.enabled,
    project_name: input.projectName,
    selected_scopes: input.selectedScopes,
  };
}
