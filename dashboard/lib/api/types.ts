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
