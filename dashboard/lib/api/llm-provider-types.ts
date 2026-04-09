// LLM Provider Types
// These match the PR-Agent API schema

export type LLMProviderType =
  | "openai"
  | "anthropic"
  | "cohere"
  | "replicate"
  | "groq"
  | "xai"
  | "huggingface"
  | "ollama"
  | "vertexai"
  | "google_ai_studio"
  | "deepseek"
  | "deepinfra"
  | "azure_openai"
  | "azure_ad"
  | "openrouter"
  | "aws_bedrock"
  | "litellm";

export type OpenAIApiType = "openai" | "azure";

// Frontend model (camelCase)
export interface LLMProvider {
  id: number;
  type: LLMProviderType;
  name: string;
  isActive: boolean;
  isDefault: boolean;
  // Optional fields based on provider type
  apiBase: string | null;
  organization: string | null;
  apiType: OpenAIApiType | null;
  apiVersion: string | null;
  deploymentId: string | null;
  // Vertex AI specific
  vertexProject: string | null;
  vertexLocation: string | null;
  // AWS Bedrock specific
  awsRegionName: string | null;
  modelId: string | null;
  createdAt: string;
  updatedAt: string;
}

// API response model (snake_case) - as returned by PR-Agent API
export interface LLMProviderApiResponse {
  id: number;
  type: LLMProviderType;
  name: string;
  is_active: boolean;
  is_default: boolean;
  api_base: string | null;
  organization: string | null;
  api_type: OpenAIApiType | null;
  api_version: string | null;
  deployment_id: string | null;
  vertex_project: string | null;
  vertex_location: string | null;
  aws_region_name: string | null;
  model_id: string | null;
  created_at: string;
  updated_at: string;
}

// API request model for creating (snake_case)
export interface CreateLLMProviderApiRequest {
  type: LLMProviderType;
  name: string;
  is_active?: boolean;
  is_default?: boolean;
  // Credentials (sensitive - not returned by API)
  api_key?: string;
  client_id?: string;
  client_secret?: string;
  tenant_id?: string;
  aws_access_key_id?: string;
  aws_secret_access_key?: string;
  // Configuration fields
  api_base?: string | null;
  organization?: string | null;
  api_type?: OpenAIApiType;
  api_version?: string | null;
  deployment_id?: string | null;
  vertex_project?: string | null;
  vertex_location?: string | null;
  aws_region_name?: string | null;
  model_id?: string | null;
  fallback_deployments?: string[] | null;
  extra_body?: Record<string, unknown> | null;
}

// Frontend input for creating
export interface CreateLLMProviderInput {
  type: LLMProviderType;
  name: string;
  isActive?: boolean;
  isDefault?: boolean;
  // Credentials
  apiKey?: string;
  clientId?: string;
  clientSecret?: string;
  tenantId?: string;
  awsAccessKeyId?: string;
  awsSecretAccessKey?: string;
  // Configuration
  apiBase?: string;
  organization?: string;
  apiType?: OpenAIApiType;
  apiVersion?: string;
  deploymentId?: string;
  vertexProject?: string;
  vertexLocation?: string;
  awsRegionName?: string;
  modelId?: string;
}

// API request model for updating (snake_case)
export interface UpdateLLMProviderApiRequest {
  name?: string;
  is_active?: boolean;
  is_default?: boolean;
  // Credentials
  api_key?: string;
  client_id?: string;
  client_secret?: string;
  tenant_id?: string;
  aws_access_key_id?: string;
  aws_secret_access_key?: string;
  // Configuration
  api_base?: string | null;
  organization?: string | null;
  api_type?: OpenAIApiType;
  api_version?: string | null;
  deployment_id?: string | null;
  vertex_project?: string | null;
  vertex_location?: string | null;
  aws_region_name?: string | null;
  model_id?: string | null;
}

// Frontend input for updating
export interface UpdateLLMProviderInput {
  id: number;
  name?: string;
  isActive?: boolean;
  isDefault?: boolean;
  // Credentials
  apiKey?: string;
  clientId?: string;
  clientSecret?: string;
  tenantId?: string;
  awsAccessKeyId?: string;
  awsSecretAccessKey?: string;
  // Configuration
  apiBase?: string;
  organization?: string;
  apiType?: OpenAIApiType;
  apiVersion?: string;
  deploymentId?: string;
  vertexProject?: string;
  vertexLocation?: string;
  awsRegionName?: string;
  modelId?: string;
}

// Re-export ApiResponse from types
export type { ApiResponse } from "./types";

// Transform functions
export function transformApiResponseToProvider(
  apiResponse: LLMProviderApiResponse,
): LLMProvider {
  return {
    id: apiResponse.id,
    type: apiResponse.type,
    name: apiResponse.name,
    isActive: apiResponse.is_active,
    isDefault: apiResponse.is_default,
    apiBase: apiResponse.api_base,
    organization: apiResponse.organization,
    apiType: apiResponse.api_type,
    apiVersion: apiResponse.api_version,
    deploymentId: apiResponse.deployment_id,
    vertexProject: apiResponse.vertex_project,
    vertexLocation: apiResponse.vertex_location,
    awsRegionName: apiResponse.aws_region_name,
    modelId: apiResponse.model_id,
    createdAt: apiResponse.created_at,
    updatedAt: apiResponse.updated_at,
  };
}

export function transformCreateInputToApiRequest(
  input: CreateLLMProviderInput,
): CreateLLMProviderApiRequest {
  return {
    type: input.type,
    name: input.name,
    is_active: input.isActive,
    is_default: input.isDefault,
    api_key: input.apiKey,
    client_id: input.clientId,
    client_secret: input.clientSecret,
    tenant_id: input.tenantId,
    aws_access_key_id: input.awsAccessKeyId,
    aws_secret_access_key: input.awsSecretAccessKey,
    api_base: input.apiBase || null,
    organization: input.organization || null,
    api_type: input.apiType,
    api_version: input.apiVersion || null,
    deployment_id: input.deploymentId || null,
    vertex_project: input.vertexProject || null,
    vertex_location: input.vertexLocation || null,
    aws_region_name: input.awsRegionName || null,
    model_id: input.modelId || null,
  };
}

export function transformUpdateInputToApiRequest(
  input: UpdateLLMProviderInput,
): UpdateLLMProviderApiRequest {
  return {
    name: input.name,
    is_active: input.isActive,
    is_default: input.isDefault,
    api_key: input.apiKey,
    client_id: input.clientId,
    client_secret: input.clientSecret,
    tenant_id: input.tenantId,
    aws_access_key_id: input.awsAccessKeyId,
    aws_secret_access_key: input.awsSecretAccessKey,
    api_base: input.apiBase,
    organization: input.organization,
    api_type: input.apiType,
    api_version: input.apiVersion,
    deployment_id: input.deploymentId,
    vertex_project: input.vertexProject,
    vertex_location: input.vertexLocation,
    aws_region_name: input.awsRegionName,
    model_id: input.modelId,
  };
}

// Provider type configuration - which fields each provider needs
export interface ProviderFieldConfig {
  apiKey: boolean;
  apiBase: boolean;
  organization: boolean;
  apiType: boolean;
  apiVersion: boolean;
  deploymentId: boolean;
  vertexProject: boolean;
  vertexLocation: boolean;
  awsAccessKeyId: boolean;
  awsSecretAccessKey: boolean;
  awsRegionName: boolean;
  clientId: boolean;
  clientSecret: boolean;
  tenantId: boolean;
  modelId: boolean;
}

const defaultFieldConfig: ProviderFieldConfig = {
  apiKey: true,
  apiBase: false,
  organization: false,
  apiType: false,
  apiVersion: false,
  deploymentId: false,
  vertexProject: false,
  vertexLocation: false,
  awsAccessKeyId: false,
  awsSecretAccessKey: false,
  awsRegionName: false,
  clientId: false,
  clientSecret: false,
  tenantId: false,
  modelId: false,
};

export const providerFieldConfigs: Record<
  LLMProviderType,
  ProviderFieldConfig
> = {
  openai: {
    ...defaultFieldConfig,
    apiBase: true,
    organization: true,
  },
  anthropic: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  cohere: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  replicate: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  groq: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  xai: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  huggingface: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  ollama: {
    ...defaultFieldConfig,
    apiKey: false,
    apiBase: true,
  },
  vertexai: {
    ...defaultFieldConfig,
    apiKey: false,
    vertexProject: true,
    vertexLocation: true,
  },
  google_ai_studio: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  deepseek: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  deepinfra: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  azure_openai: {
    ...defaultFieldConfig,
    apiBase: true,
    apiVersion: true,
    deploymentId: true,
  },
  azure_ad: {
    ...defaultFieldConfig,
    apiKey: false,
    clientId: true,
    clientSecret: true,
    tenantId: true,
    apiBase: true,
  },
  openrouter: {
    ...defaultFieldConfig,
    apiBase: true,
  },
  aws_bedrock: {
    ...defaultFieldConfig,
    apiKey: false,
    awsAccessKeyId: true,
    awsSecretAccessKey: true,
    awsRegionName: true,
    modelId: true,
  },
  litellm: {
    ...defaultFieldConfig,
    apiBase: true,
  },
};
