"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  createLLMProvider,
  updateLLMProvider,
  fetchProviderModels,
  MODEL_FETCHABLE_PROVIDERS,
  DEFAULT_OPENAI_API_BASE,
  DEFAULT_MODELS_BY_API_BASE,
} from "@/lib/api/llm-providers";
import { normalizeApiBaseUrl } from "@/lib/validators";
import type {
  LLMProvider,
  LLMProviderType,
} from "@/lib/api/llm-provider-types";
import { providerFieldConfigs } from "@/lib/api/llm-provider-types";

interface LLMProviderFormProps {
  provider?: LLMProvider;
  lang: string;
}

const providerTypes: { value: LLMProviderType; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "huggingface", label: "Hugging Face" },
  { value: "ollama", label: "Ollama" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "litellm", label: "LiteLLM" },
];

export function LLMProviderForm({ provider, lang }: LLMProviderFormProps) {
  const dict = useDictionary();
  const router = useRouter();
  const isEdit = !!provider;

  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<LLMProviderType>(
    provider?.type ?? "openai",
  );

  // Password visibility toggles
  const [showApiKey, setShowApiKey] = useState(false);
  const [showClientSecret, setShowClientSecret] = useState(false);
  const [showAwsSecretKey, setShowAwsSecretKey] = useState(false);

  // Model fetching state
  const [apiKeyValue, setApiKeyValue] = useState("");
  const [apiBaseValue, setApiBaseValue] = useState(
    provider?.apiBase ?? "https://netmind.viettel.vn/gateway/v1",
  );
  const [lastFetchedApiBase, setLastFetchedApiBase] = useState<string | null>(
    null,
  );
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [modelsFetched, setModelsFetched] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // Model selection state
  const [selectedModel, setSelectedModel] = useState(provider?.modelId ?? "");
  const [fallbackModels, setFallbackModels] = useState<string[]>([]);

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fieldConfig = providerFieldConfigs[selectedType];
  const canFetchModels = MODEL_FETCHABLE_PROVIDERS.includes(
    selectedType as (typeof MODEL_FETCHABLE_PROVIDERS)[number],
  );

  // Handle API base URL change - clear default model if changing away from a known default
  const handleApiBaseChange = (newApiBase: string) => {
    setApiBaseValue(newApiBase);

    if (!canFetchModels) return;

    const normalizedApiBase = normalizeApiBaseUrl(
      newApiBase,
      DEFAULT_OPENAI_API_BASE,
    );

    // If not the netmind URL and we have a default model selected, clear it
    const defaultModel = DEFAULT_MODELS_BY_API_BASE[normalizedApiBase];
    if (!defaultModel && selectedModel) {
      // Check if current model is a default model from another API base
      const isDefaultFromOtherBase = Object.values(
        DEFAULT_MODELS_BY_API_BASE,
      ).includes(selectedModel);
      if (isDefaultFromOtherBase) {
        setSelectedModel("");
      }
    }
  };

  // Handle provider type change - reset all model state
  const handleTypeChange = (value: string | null) => {
    if (!value) return;
    setSelectedType(value as LLMProviderType);
    setAvailableModels([]);
    setModelsFetched(false);
    setModelsError(null);
    setSelectedModel("");
    setFallbackModels([]);
    setLastFetchedApiBase(null);
  };

  // Auto-fetch models when API key or API base URL changes (debounced)
  useEffect(() => {
    if (!canFetchModels || !apiKeyValue || apiKeyValue.length < 10) {
      return;
    }

    // Normalize the API base URL with fallback
    const normalizedApiBase = normalizeApiBaseUrl(
      apiBaseValue,
      DEFAULT_OPENAI_API_BASE,
    );

    // Skip if we already fetched for this API base (unless API key changed)
    const fetchKey = `${apiKeyValue}:${normalizedApiBase}`;
    if (lastFetchedApiBase === fetchKey) {
      return;
    }

    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new debounced fetch
    debounceTimerRef.current = setTimeout(async () => {
      setFetchingModels(true);
      setModelsError(null);

      const result = await fetchProviderModels(
        selectedType,
        apiKeyValue,
        normalizedApiBase,
      );

      setFetchingModels(false);
      setLastFetchedApiBase(fetchKey);

      if (result.success && result.data) {
        setAvailableModels(result.data);
        setModelsFetched(true);
        setModelsError(null);

        // Set default model based on API base, or clear if not matching
        const defaultModel = DEFAULT_MODELS_BY_API_BASE[normalizedApiBase];
        if (defaultModel && result.data.includes(defaultModel)) {
          setSelectedModel(defaultModel);
        } else if (
          selectedModel &&
          Object.values(DEFAULT_MODELS_BY_API_BASE).includes(selectedModel)
        ) {
          // Clear selected model if it was a default from another API base
          setSelectedModel("");
        }
      } else {
        setModelsError(
          result.error || dict.llmProviders.form.fetchModelsFailed,
        );
        setAvailableModels([]);
        setModelsFetched(false);
      }
    }, 800); // 800ms debounce

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [
    apiKeyValue,
    apiBaseValue,
    selectedType,
    canFetchModels,
    dict.llmProviders.form.fetchModelsFailed,
    lastFetchedApiBase,
    selectedModel,
  ]);

  function handleRemoveFallbackModel(model: string) {
    setFallbackModels(fallbackModels.filter((m) => m !== model));
  }

  function handleFallbackModelsChange(value: string | null) {
    if (value && !fallbackModels.includes(value)) {
      setFallbackModels([...fallbackModels, value]);
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrors({});
    setError(null);
    setPending(true);

    const formData = new FormData(e.currentTarget);

    try {
      let result;
      if (isEdit && provider) {
        result = await updateLLMProvider({
          id: provider.id,
          name: formData.get("name") as string,
          apiKey: (formData.get("apiKey") as string) || undefined,
          apiBase: (formData.get("apiBase") as string) || undefined,
          organization: (formData.get("organization") as string) || undefined,
          apiVersion: (formData.get("apiVersion") as string) || undefined,
          deploymentId: (formData.get("deploymentId") as string) || undefined,
          vertexProject: (formData.get("vertexProject") as string) || undefined,
          vertexLocation:
            (formData.get("vertexLocation") as string) || undefined,
          awsAccessKeyId:
            (formData.get("awsAccessKeyId") as string) || undefined,
          awsSecretAccessKey:
            (formData.get("awsSecretAccessKey") as string) || undefined,
          awsRegionName: (formData.get("awsRegionName") as string) || undefined,
          clientId: (formData.get("clientId") as string) || undefined,
          clientSecret: (formData.get("clientSecret") as string) || undefined,
          tenantId: (formData.get("tenantId") as string) || undefined,
          modelId: (formData.get("modelId") as string) || undefined,
        });
      } else {
        result = await createLLMProvider({
          type: formData.get("type") as LLMProviderType,
          name: formData.get("name") as string,
          apiKey: (formData.get("apiKey") as string) || undefined,
          apiBase: (formData.get("apiBase") as string) || undefined,
          organization: (formData.get("organization") as string) || undefined,
          apiVersion: (formData.get("apiVersion") as string) || undefined,
          deploymentId: (formData.get("deploymentId") as string) || undefined,
          vertexProject: (formData.get("vertexProject") as string) || undefined,
          vertexLocation:
            (formData.get("vertexLocation") as string) || undefined,
          awsAccessKeyId:
            (formData.get("awsAccessKeyId") as string) || undefined,
          awsSecretAccessKey:
            (formData.get("awsSecretAccessKey") as string) || undefined,
          awsRegionName: (formData.get("awsRegionName") as string) || undefined,
          clientId: (formData.get("clientId") as string) || undefined,
          clientSecret: (formData.get("clientSecret") as string) || undefined,
          tenantId: (formData.get("tenantId") as string) || undefined,
          modelId: (formData.get("modelId") as string) || undefined,
        });
      }

      if (!result.success) {
        setError(result.error || "An error occurred");
        if (result.fieldErrors) {
          setErrors(result.fieldErrors);
        }
        setPending(false);
        return;
      }

      router.push(`/${lang}/llm-providers`);
      router.refresh();
    } catch {
      setError(dict.llmProviders.form.errorGeneric);
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Provider Type */}
      <div className="space-y-2">
        <Label htmlFor="type">
          {dict.llmProviders.form.type}
          <span className="ml-1 text-destructive">*</span>
        </Label>
        <Select
          name="type"
          value={selectedType}
          onValueChange={handleTypeChange}
          disabled={isEdit}
        >
          <SelectTrigger id="type">
            <SelectValue placeholder={dict.llmProviders.form.selectType}>
              {(value) =>
                providerTypes.find((t) => t.value === value)?.label ?? value
              }
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {providerTypes.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.type && (
          <p className="text-sm text-destructive">{errors.type}</p>
        )}
        {isEdit && (
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.typeCannotChange}
          </p>
        )}
      </div>

      {/* Display Name */}
      <div className="space-y-2">
        <Label htmlFor="name">
          {dict.llmProviders.form.name}
          <span className="ml-1 text-destructive">*</span>
        </Label>
        <Input
          id="name"
          name="name"
          defaultValue={provider?.name}
          placeholder={dict.llmProviders.form.namePlaceholder}
          required
          aria-invalid={!!errors.name}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name}</p>
        )}
        <p className="text-sm text-muted-foreground">
          {dict.llmProviders.form.nameHelp}
        </p>
      </div>

      {/* Organization (OpenAI) */}
      {fieldConfig.organization && (
        <div className="space-y-2">
          <Label htmlFor="organization">
            {dict.llmProviders.form.organization}
          </Label>
          <Input
            id="organization"
            name="organization"
            defaultValue={provider?.organization ?? ""}
            placeholder={dict.llmProviders.form.organizationPlaceholder}
            aria-invalid={!!errors.organization}
          />
          {errors.organization && (
            <p className="text-sm text-destructive">{errors.organization}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.organizationHelp}
          </p>
        </div>
      )}

      {/* API Key (for most providers) */}
      {fieldConfig.apiKey && (
        <div className="space-y-2">
          <Label htmlFor="apiKey">
            {dict.llmProviders.form.apiKey}
            {!isEdit && <span className="ml-1 text-destructive">*</span>}
          </Label>
          <div className="relative">
            <Input
              id="apiKey"
              name="apiKey"
              type={showApiKey ? "text" : "password"}
              placeholder={
                isEdit
                  ? dict.llmProviders.form.apiKeyPlaceholderEdit
                  : dict.llmProviders.form.apiKeyPlaceholder
              }
              required={!isEdit}
              aria-invalid={!!errors.apiKey}
              className="pr-16"
              value={apiKeyValue}
              onChange={(e) => setApiKeyValue(e.target.value)}
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
              {fetchingModels && (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={
                  showApiKey
                    ? dict.llmProviders.form.hideKey
                    : dict.llmProviders.form.showKey
                }
              >
                {showApiKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
          {errors.apiKey && (
            <p className="text-sm text-destructive">{errors.apiKey}</p>
          )}
          {modelsError && (
            <p className="text-sm text-destructive">{modelsError}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.apiKeyHelp}
            {canFetchModels && ` ${dict.llmProviders.form.modelsAutoFetch}`}
          </p>
        </div>
      )}

      {/* API Base URL */}
      {fieldConfig.apiBase && (
        <div className="space-y-2">
          <Label htmlFor="apiBase">
            {dict.llmProviders.form.apiBase}
            <span className="ml-2 text-sm text-muted-foreground">
              ({dict.llmProviders.form.optional})
            </span>
          </Label>
          <Input
            id="apiBase"
            name="apiBase"
            type="url"
            value={apiBaseValue}
            onChange={(e) => handleApiBaseChange(e.target.value)}
            placeholder={dict.llmProviders.form.apiBasePlaceholder}
            aria-invalid={!!errors.apiBase}
          />
          {errors.apiBase && (
            <p className="text-sm text-destructive">{errors.apiBase}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.apiBaseHelp}
          </p>
        </div>
      )}

      {/* Model Selection (for providers that support model fetching) */}
      {canFetchModels && (
        <div className="space-y-2">
          <Label htmlFor="model">
            {dict.llmProviders.form.model}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          {modelsFetched && availableModels.length > 0 ? (
            <Select
              name="model"
              value={selectedModel}
              onValueChange={(value) => setSelectedModel(value ?? "")}
              required
            >
              <SelectTrigger id="model">
                <SelectValue placeholder={dict.llmProviders.form.selectModel} />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model} value={model}>
                    {model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              id="model"
              name="model"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder={dict.llmProviders.form.modelPlaceholder}
              required
            />
          )}
          <p className="text-sm text-muted-foreground">
            {modelsFetched
              ? dict.llmProviders.form.modelHelpFetched
              : dict.llmProviders.form.modelHelp}
          </p>
        </div>
      )}

      {/* Fallback Models (for providers that support model fetching) */}
      {canFetchModels && (
        <div className="space-y-2">
          <Label>{dict.llmProviders.form.fallbackModels}</Label>

          {/* Selected fallback models as tags */}
          {fallbackModels.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {fallbackModels.map((model) => (
                <span
                  key={model}
                  className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-sm"
                >
                  {model}
                  <button
                    type="button"
                    onClick={() => handleRemoveFallbackModel(model)}
                    className="text-muted-foreground hover:text-foreground"
                    aria-label={`Remove ${model}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Multi-select dropdown for fallback models */}
          {modelsFetched && availableModels.length > 0 ? (
            <Select value="" onValueChange={handleFallbackModelsChange}>
              <SelectTrigger>
                <SelectValue
                  placeholder={dict.llmProviders.form.selectFallbackModel}
                />
              </SelectTrigger>
              <SelectContent>
                {availableModels
                  .filter(
                    (m) => m !== selectedModel && !fallbackModels.includes(m),
                  )
                  .map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              placeholder={dict.llmProviders.form.fallbackModelPlaceholder}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const value = e.currentTarget.value.trim();
                  if (value && !fallbackModels.includes(value)) {
                    setFallbackModels([...fallbackModels, value]);
                    e.currentTarget.value = "";
                  }
                }
              }}
            />
          )}

          {/* Hidden input to submit fallback models */}
          <input
            type="hidden"
            name="fallbackModels"
            value={fallbackModels.join(",")}
          />

          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.fallbackModelsHelp}
          </p>
        </div>
      )}

      {/* API Version (Azure OpenAI) */}
      {fieldConfig.apiVersion && (
        <div className="space-y-2">
          <Label htmlFor="apiVersion">
            {dict.llmProviders.form.apiVersion}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <Input
            id="apiVersion"
            name="apiVersion"
            defaultValue={provider?.apiVersion ?? ""}
            placeholder={dict.llmProviders.form.apiVersionPlaceholder}
            required
            aria-invalid={!!errors.apiVersion}
          />
          {errors.apiVersion && (
            <p className="text-sm text-destructive">{errors.apiVersion}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.apiVersionHelp}
          </p>
        </div>
      )}

      {/* Deployment ID (Azure OpenAI) */}
      {fieldConfig.deploymentId && (
        <div className="space-y-2">
          <Label htmlFor="deploymentId">
            {dict.llmProviders.form.deploymentId}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <Input
            id="deploymentId"
            name="deploymentId"
            defaultValue={provider?.deploymentId ?? ""}
            placeholder={dict.llmProviders.form.deploymentIdPlaceholder}
            required
            aria-invalid={!!errors.deploymentId}
          />
          {errors.deploymentId && (
            <p className="text-sm text-destructive">{errors.deploymentId}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.deploymentIdHelp}
          </p>
        </div>
      )}

      {/* Vertex AI Project */}
      {fieldConfig.vertexProject && (
        <div className="space-y-2">
          <Label htmlFor="vertexProject">
            {dict.llmProviders.form.vertexProject}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <Input
            id="vertexProject"
            name="vertexProject"
            defaultValue={provider?.vertexProject ?? ""}
            placeholder={dict.llmProviders.form.vertexProjectPlaceholder}
            required
            aria-invalid={!!errors.vertexProject}
          />
          {errors.vertexProject && (
            <p className="text-sm text-destructive">{errors.vertexProject}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.vertexProjectHelp}
          </p>
        </div>
      )}

      {/* Vertex AI Location */}
      {fieldConfig.vertexLocation && (
        <div className="space-y-2">
          <Label htmlFor="vertexLocation">
            {dict.llmProviders.form.vertexLocation}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <Input
            id="vertexLocation"
            name="vertexLocation"
            defaultValue={provider?.vertexLocation ?? ""}
            placeholder={dict.llmProviders.form.vertexLocationPlaceholder}
            required
            aria-invalid={!!errors.vertexLocation}
          />
          {errors.vertexLocation && (
            <p className="text-sm text-destructive">{errors.vertexLocation}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.vertexLocationHelp}
          </p>
        </div>
      )}

      {/* Azure AD Client ID */}
      {fieldConfig.clientId && (
        <div className="space-y-2">
          <Label htmlFor="clientId">
            {dict.llmProviders.form.clientId}
            {!isEdit && <span className="ml-1 text-destructive">*</span>}
          </Label>
          <Input
            id="clientId"
            name="clientId"
            placeholder={dict.llmProviders.form.clientIdPlaceholder}
            required={!isEdit}
            aria-invalid={!!errors.clientId}
          />
          {errors.clientId && (
            <p className="text-sm text-destructive">{errors.clientId}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.clientIdHelp}
          </p>
        </div>
      )}

      {/* Azure AD Client Secret */}
      {fieldConfig.clientSecret && (
        <div className="space-y-2">
          <Label htmlFor="clientSecret">
            {dict.llmProviders.form.clientSecret}
            {!isEdit && <span className="ml-1 text-destructive">*</span>}
          </Label>
          <div className="relative">
            <Input
              id="clientSecret"
              name="clientSecret"
              type={showClientSecret ? "text" : "password"}
              placeholder={
                isEdit
                  ? dict.llmProviders.form.clientSecretPlaceholderEdit
                  : dict.llmProviders.form.clientSecretPlaceholder
              }
              required={!isEdit}
              aria-invalid={!!errors.clientSecret}
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowClientSecret(!showClientSecret)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={
                showClientSecret
                  ? dict.llmProviders.form.hideKey
                  : dict.llmProviders.form.showKey
              }
            >
              {showClientSecret ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.clientSecret && (
            <p className="text-sm text-destructive">{errors.clientSecret}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.clientSecretHelp}
          </p>
        </div>
      )}

      {/* Azure AD Tenant ID */}
      {fieldConfig.tenantId && (
        <div className="space-y-2">
          <Label htmlFor="tenantId">
            {dict.llmProviders.form.tenantId}
            {!isEdit && <span className="ml-1 text-destructive">*</span>}
          </Label>
          <Input
            id="tenantId"
            name="tenantId"
            placeholder={dict.llmProviders.form.tenantIdPlaceholder}
            required={!isEdit}
            aria-invalid={!!errors.tenantId}
          />
          {errors.tenantId && (
            <p className="text-sm text-destructive">{errors.tenantId}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.tenantIdHelp}
          </p>
        </div>
      )}

      {/* AWS Access Key ID */}
      {fieldConfig.awsAccessKeyId && (
        <div className="space-y-2">
          <Label htmlFor="awsAccessKeyId">
            {dict.llmProviders.form.awsAccessKeyId}
            {!isEdit && <span className="ml-1 text-destructive">*</span>}
          </Label>
          <Input
            id="awsAccessKeyId"
            name="awsAccessKeyId"
            placeholder={dict.llmProviders.form.awsAccessKeyIdPlaceholder}
            required={!isEdit}
            aria-invalid={!!errors.awsAccessKeyId}
          />
          {errors.awsAccessKeyId && (
            <p className="text-sm text-destructive">{errors.awsAccessKeyId}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.awsAccessKeyIdHelp}
          </p>
        </div>
      )}

      {/* AWS Secret Access Key */}
      {fieldConfig.awsSecretAccessKey && (
        <div className="space-y-2">
          <Label htmlFor="awsSecretAccessKey">
            {dict.llmProviders.form.awsSecretAccessKey}
            {!isEdit && <span className="ml-1 text-destructive">*</span>}
          </Label>
          <div className="relative">
            <Input
              id="awsSecretAccessKey"
              name="awsSecretAccessKey"
              type={showAwsSecretKey ? "text" : "password"}
              placeholder={
                isEdit
                  ? dict.llmProviders.form.awsSecretAccessKeyPlaceholderEdit
                  : dict.llmProviders.form.awsSecretAccessKeyPlaceholder
              }
              required={!isEdit}
              aria-invalid={!!errors.awsSecretAccessKey}
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowAwsSecretKey(!showAwsSecretKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={
                showAwsSecretKey
                  ? dict.llmProviders.form.hideKey
                  : dict.llmProviders.form.showKey
              }
            >
              {showAwsSecretKey ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.awsSecretAccessKey && (
            <p className="text-sm text-destructive">
              {errors.awsSecretAccessKey}
            </p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.awsSecretAccessKeyHelp}
          </p>
        </div>
      )}

      {/* AWS Region */}
      {fieldConfig.awsRegionName && (
        <div className="space-y-2">
          <Label htmlFor="awsRegionName">
            {dict.llmProviders.form.awsRegionName}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <Input
            id="awsRegionName"
            name="awsRegionName"
            defaultValue={provider?.awsRegionName ?? ""}
            placeholder={dict.llmProviders.form.awsRegionNamePlaceholder}
            required
            aria-invalid={!!errors.awsRegionName}
          />
          {errors.awsRegionName && (
            <p className="text-sm text-destructive">{errors.awsRegionName}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.awsRegionNameHelp}
          </p>
        </div>
      )}

      {/* Model ID (AWS Bedrock) */}
      {fieldConfig.modelId && (
        <div className="space-y-2">
          <Label htmlFor="modelId">
            {dict.llmProviders.form.modelId}
            <span className="ml-2 text-sm text-muted-foreground">
              ({dict.llmProviders.form.optional})
            </span>
          </Label>
          <Input
            id="modelId"
            name="modelId"
            defaultValue={provider?.modelId ?? ""}
            placeholder={dict.llmProviders.form.modelIdPlaceholder}
            aria-invalid={!!errors.modelId}
          />
          {errors.modelId && (
            <p className="text-sm text-destructive">{errors.modelId}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.llmProviders.form.modelIdHelp}
          </p>
        </div>
      )}

      {/* Form Actions */}
      <div className="flex gap-3">
        <Button type="submit" disabled={pending}>
          {pending
            ? dict.llmProviders.form.saving
            : isEdit
              ? dict.llmProviders.form.update
              : dict.llmProviders.form.create}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push(`/${lang}/llm-providers`)}
          disabled={pending}
        >
          {dict.llmProviders.form.cancel}
        </Button>
      </div>
    </form>
  );
}
