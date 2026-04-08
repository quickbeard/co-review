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

export interface GitProvider {
  id: string;
  type: GitProviderType;
  name: string;
  baseUrl: string | null;
  isActive: boolean;
  deploymentType: GitHubDeploymentType | null; // Only for GitHub
  createdAt: string;
  updatedAt: string;
}

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

export interface UpdateGitProviderInput {
  id: string;
  name?: string;
  baseUrl?: string;
  accessToken?: string;
  deploymentType?: GitHubDeploymentType;
  appId?: string;
  privateKey?: string;
  webhookSecret?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  fieldErrors?: Record<string, string>;
}
