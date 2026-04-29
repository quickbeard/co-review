"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  createGitProvider,
  enqueueDevLakeSync,
  previewDevLakeRemoteScopes,
  updateDevLakeIntegration,
  updateGitProvider,
} from "@/lib/api/git-providers";
import type {
  DevLakeRemoteScope,
  GitProvider,
  GitProviderType,
  GitHubDeploymentType,
} from "@/lib/api/types";

interface GitProviderFormProps {
  provider?: GitProvider;
  lang: string;
}

const providerTypes: { value: GitProviderType; label: string }[] = [
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
  { value: "bitbucket", label: "Bitbucket" },
  { value: "azure_devops", label: "Azure DevOps" },
  { value: "gitea", label: "Gitea" },
  { value: "gerrit", label: "Gerrit" },
];

// Providers that support self-hosted instances
const selfHostedProviders: GitProviderType[] = [
  "gitlab",
  "gitea",
  "gerrit",
  "bitbucket",
];

export function GitProviderForm({ provider, lang }: GitProviderFormProps) {
  const dict = useDictionary();
  const router = useRouter();
  const isEdit = !!provider;
  const formRef = useRef<HTMLFormElement>(null);

  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<GitProviderType>(
    provider?.type ?? "github",
  );
  const [deploymentType, setDeploymentType] = useState<GitHubDeploymentType>(
    provider?.deploymentType ?? "user",
  );

  // Password visibility toggles
  const [showAccessToken, setShowAccessToken] = useState(false);
  const [showPrivateKey, setShowPrivateKey] = useState(false);
  const [showWebhookSecret, setShowWebhookSecret] = useState(false);
  const [autoSyncOnCreate, setAutoSyncOnCreate] = useState(false);
  const [autoSyncProjectName, setAutoSyncProjectName] = useState("");
  const [loadingScopes, setLoadingScopes] = useState(false);
  const [availableScopes, setAvailableScopes] = useState<DevLakeRemoteScope[]>([]);
  const [selectedScopeIds, setSelectedScopeIds] = useState<Set<string>>(new Set());

  const showBaseUrl = selfHostedProviders.includes(selectedType);
  const isGitHub = selectedType === "github";

  function toFriendlyError(rawError?: string): string {
    if (!rawError) return "An error occurred";
    const normalized = rawError.toLowerCase();
    if (
      normalized.includes("scope config is duplicated") ||
      (normalized.includes("duplicated") && normalized.includes("devlake"))
    ) {
      return dict.gitProviders.form.autoSyncDuplicateConnectionName;
    }
    return rawError;
  }

  function toScopeId(scope: Record<string, unknown>): string | null {
    const raw = scope.scopeId ?? scope.id;
    if (raw === undefined || raw === null) return null;
    return String(raw);
  }

  function toScopePayload(scope: DevLakeRemoteScope): Record<string, unknown> | null {
    const scopeId = toScopeId(scope as Record<string, unknown>);
    if (!scopeId) return null;
    return {
      scopeId,
      name: typeof scope.name === "string" ? scope.name : undefined,
      fullName: typeof scope.fullName === "string" ? scope.fullName : undefined,
    };
  }

  async function loadPreviewScopes() {
    if (isEdit || !formRef.current || !autoSyncOnCreate) return;
    const formData = new FormData(formRef.current);
    const name = String(formData.get("name") || "").trim();
    const baseUrl = String(formData.get("baseUrl") || "").trim();
    const accessToken = String(formData.get("accessToken") || "").trim();
    const appId = String(formData.get("appId") || "").trim();
    const privateKey = String(formData.get("privateKey") || "").trim();
    const webhookSecret = String(formData.get("webhookSecret") || "").trim();

    if (!name) {
      setAvailableScopes([]);
      setSelectedScopeIds(new Set());
      return;
    }

    setLoadingScopes(true);
    const result = await previewDevLakeRemoteScopes({
      type: selectedType,
      name,
      baseUrl: baseUrl || undefined,
      accessToken: accessToken || undefined,
      deploymentType: isGitHub ? deploymentType : undefined,
      appId: appId || undefined,
      privateKey: privateKey || undefined,
      webhookSecret: webhookSecret || undefined,
    });
    setLoadingScopes(false);

    if (!result.success || !result.data) {
      setAvailableScopes([]);
      setSelectedScopeIds(new Set());
      setError(toFriendlyError(result.error));
      return;
    }
    setAvailableScopes(result.data.scopes || []);
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
        result = await updateGitProvider({
          id: provider.id,
          name: formData.get("name") as string,
          baseUrl: (formData.get("baseUrl") as string) || undefined,
          accessToken: (formData.get("accessToken") as string) || undefined,
          deploymentType: isGitHub ? deploymentType : undefined,
          appId: (formData.get("appId") as string) || undefined,
          privateKey: (formData.get("privateKey") as string) || undefined,
          webhookSecret: (formData.get("webhookSecret") as string) || undefined,
        });
      } else {
        const createResult = await createGitProvider({
          type: formData.get("type") as GitProviderType,
          name: formData.get("name") as string,
          baseUrl: (formData.get("baseUrl") as string) || undefined,
          accessToken: (formData.get("accessToken") as string) || undefined,
          deploymentType: isGitHub ? deploymentType : undefined,
          appId: (formData.get("appId") as string) || undefined,
          privateKey: (formData.get("privateKey") as string) || undefined,
          webhookSecret: (formData.get("webhookSecret") as string) || undefined,
          },
          {
            // Create first, then apply selected scopes + trigger sync explicitly.
            autoSyncOnCreate: false,
          },
        );
        result = createResult;
        if (
          autoSyncOnCreate &&
          createResult.success &&
          createResult.data
        ) {
          const selectedScopesPayload = availableScopes
            .filter((scope) => {
              const scopeId = toScopeId(scope as Record<string, unknown>);
              return scopeId ? selectedScopeIds.has(scopeId) : false;
            })
            .map(toScopePayload)
            .filter((scope): scope is Record<string, unknown> => scope !== null);
          const integrationResult = await updateDevLakeIntegration(createResult.data.id, {
            enabled: true,
            projectName: autoSyncProjectName || undefined,
            selectedScopes: selectedScopesPayload,
          });
          if (!integrationResult.success) {
            setError(toFriendlyError(integrationResult.error));
            setPending(false);
            return;
          }
          const syncResult = await enqueueDevLakeSync(createResult.data.id);
          if (!syncResult.success) {
            setError(toFriendlyError(syncResult.error));
            setPending(false);
            return;
          }
        }
      }

      if (!result.success) {
        setError(toFriendlyError(result.error));
        if (result.fieldErrors) {
          setErrors(result.fieldErrors);
        }
        setPending(false);
        return;
      }

      router.push(`/${lang}/git-providers`);
      router.refresh();
    } catch {
      setError(dict.gitProviders.form.errorGeneric);
      setPending(false);
    }
  }

  return (
    <form ref={formRef} onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Provider Type */}
      <div className="space-y-2">
        <Label htmlFor="type">
          {dict.gitProviders.form.type}
          <span className="ml-1 text-destructive">*</span>
        </Label>
        <Select
          name="type"
          value={selectedType}
          onValueChange={(value) => setSelectedType(value as GitProviderType)}
        >
          <SelectTrigger id="type">
            <SelectValue placeholder={dict.gitProviders.form.selectType}>
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
      </div>

      {/* Display Name */}
      <div className="space-y-2">
        <Label htmlFor="name">
          {dict.gitProviders.form.name}
          <span className="ml-1 text-destructive">*</span>
        </Label>
        <Input
          id="name"
          name="name"
          defaultValue={provider?.name}
          placeholder={dict.gitProviders.form.namePlaceholder}
          required
          aria-invalid={!!errors.name}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name}</p>
        )}
        <p className="text-sm text-muted-foreground">
          {dict.gitProviders.form.nameHelp}
        </p>
      </div>

      {/* Base URL (for self-hosted) */}
      {showBaseUrl && (
        <div className="space-y-2">
          <Label htmlFor="baseUrl">
            {dict.gitProviders.form.baseUrl}
            <span className="ml-2 text-sm text-muted-foreground">
              ({dict.gitProviders.form.optional})
            </span>
          </Label>
          <Input
            id="baseUrl"
            name="baseUrl"
            type="url"
            defaultValue={provider?.baseUrl ?? ""}
            placeholder={dict.gitProviders.form.baseUrlPlaceholder}
            aria-invalid={!!errors.baseUrl}
          />
          {errors.baseUrl && (
            <p className="text-sm text-destructive">{errors.baseUrl}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.gitProviders.form.baseUrlHelp}
          </p>
        </div>
      )}

      {/* GitHub Deployment Type */}
      {isGitHub && (
        <div className="space-y-3">
          <Label>
            {dict.gitProviders.form.deploymentType}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="deploymentTypeRadio"
                value="user"
                checked={deploymentType === "user"}
                onChange={() => setDeploymentType("user")}
                className="h-4 w-4 text-primary"
              />
              <span className="text-sm">
                {dict.gitProviders.form.deploymentTypeUser}
              </span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="deploymentTypeRadio"
                value="app"
                checked={deploymentType === "app"}
                onChange={() => setDeploymentType("app")}
                className="h-4 w-4 text-primary"
              />
              <span className="text-sm">
                {dict.gitProviders.form.deploymentTypeApp}
              </span>
            </label>
          </div>
          <p className="text-sm text-muted-foreground">
            {deploymentType === "user"
              ? dict.gitProviders.form.deploymentTypeUserHelp
              : dict.gitProviders.form.deploymentTypeAppHelp}
          </p>
        </div>
      )}

      {/* Access Token (for non-GitHub or GitHub user deployment) */}
      {(!isGitHub || deploymentType === "user") && (
        <div className="space-y-2">
          <Label htmlFor="accessToken">
            {isGitHub
              ? dict.gitProviders.form.userToken
              : dict.gitProviders.form.accessToken}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <div className="relative">
            <Input
              id="accessToken"
              name="accessToken"
              type={showAccessToken ? "text" : "password"}
              placeholder={
                isEdit
                  ? dict.gitProviders.form.accessTokenPlaceholderEdit
                  : dict.gitProviders.form.accessTokenPlaceholder
              }
              required={!isEdit}
              aria-invalid={!!errors.accessToken}
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowAccessToken(!showAccessToken)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={
                showAccessToken
                  ? dict.gitProviders.form.hideToken
                  : dict.gitProviders.form.showToken
              }
            >
              {showAccessToken ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.accessToken && (
            <p className="text-sm text-destructive">{errors.accessToken}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {isGitHub
              ? dict.gitProviders.form.userTokenHelp
              : dict.gitProviders.form.accessTokenHelp}
          </p>
        </div>
      )}

      {/* GitHub App fields */}
      {isGitHub && deploymentType === "app" && (
        <>
          {/* App ID */}
          <div className="space-y-2">
            <Label htmlFor="appId">
              {dict.gitProviders.form.appId}
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <Input
              id="appId"
              name="appId"
              placeholder={dict.gitProviders.form.appIdPlaceholder}
              required
              aria-invalid={!!errors.appId}
            />
            {errors.appId && (
              <p className="text-sm text-destructive">{errors.appId}</p>
            )}
            <p className="text-sm text-muted-foreground">
              {dict.gitProviders.form.appIdHelp}
            </p>
          </div>

          {/* Private Key */}
          <div className="space-y-2">
            <Label htmlFor="privateKey">
              {dict.gitProviders.form.privateKey}
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <div className="relative">
              <Textarea
                id="privateKey"
                name="privateKey"
                placeholder={dict.gitProviders.form.privateKeyPlaceholder}
                required
                rows={6}
                className="font-mono text-xs pr-10"
                aria-invalid={!!errors.privateKey}
              />
              <button
                type="button"
                onClick={() => setShowPrivateKey(!showPrivateKey)}
                className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                aria-label={
                  showPrivateKey
                    ? dict.gitProviders.form.hideToken
                    : dict.gitProviders.form.showToken
                }
              >
                {showPrivateKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.privateKey && (
              <p className="text-sm text-destructive">{errors.privateKey}</p>
            )}
            <p className="text-sm text-muted-foreground">
              {dict.gitProviders.form.privateKeyHelp}
            </p>
          </div>
        </>
      )}

      {/* Webhook Secret */}
      <div className="space-y-2">
        <Label htmlFor="webhookSecret">
          {dict.gitProviders.form.webhookSecret}
          <span className="ml-2 text-sm text-muted-foreground">
            ({dict.gitProviders.form.optional})
          </span>
        </Label>
        <div className="relative">
          <Input
            id="webhookSecret"
            name="webhookSecret"
            type={showWebhookSecret ? "text" : "password"}
            placeholder={dict.gitProviders.form.webhookSecretPlaceholder}
            aria-invalid={!!errors.webhookSecret}
            className="pr-10"
          />
          <button
            type="button"
            onClick={() => setShowWebhookSecret(!showWebhookSecret)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label={
              showWebhookSecret
                ? dict.gitProviders.form.hideToken
                : dict.gitProviders.form.showToken
            }
          >
            {showWebhookSecret ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>
        {errors.webhookSecret && (
          <p className="text-sm text-destructive">{errors.webhookSecret}</p>
        )}
        <p className="text-sm text-muted-foreground">
          {dict.gitProviders.form.webhookSecretHelp}
        </p>
      </div>

      {/* Form Actions */}
      {!isEdit && (
        <div className="space-y-3 rounded-md border border-border p-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={autoSyncOnCreate}
              onChange={(e) => {
                const next = e.target.checked;
                setAutoSyncOnCreate(next);
                if (!next) {
                  setAvailableScopes([]);
                  setSelectedScopeIds(new Set());
                  return;
                }
                setError(null);
                void loadPreviewScopes();
              }}
              className="h-4 w-4 rounded border-border text-primary"
            />
            {dict.gitProviders.form.autoSyncOnCreate}
          </label>
          {autoSyncOnCreate && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="devlake-project-name">
                  {dict.gitProviders.form.autoSyncProjectName}
                </Label>
                <Input
                  id="devlake-project-name"
                  value={autoSyncProjectName}
                  onChange={(e) => setAutoSyncProjectName(e.target.value)}
                  placeholder={dict.gitProviders.form.autoSyncProjectNamePlaceholder}
                />
                <p className="text-xs text-muted-foreground">
                  {dict.gitProviders.form.autoSyncProjectNameHelp}
                </p>
              </div>
              <div className="space-y-2">
                <Label>{dict.gitProviders.form.autoSyncScopes}</Label>
                <div
                  className="max-h-64 space-y-2 overflow-auto rounded-md border border-border bg-background px-3 py-2 text-sm"
                >
                  {loadingScopes && (
                    <p className="text-muted-foreground">{dict.gitProviders.devlake.loadingScopes}</p>
                  )}
                  {!loadingScopes && availableScopes.length === 0 && (
                    <p className="text-muted-foreground">{dict.gitProviders.devlake.noScopes}</p>
                  )}
                  {!loadingScopes &&
                    availableScopes.map((scope) => {
                      const scopeId = toScopeId(scope as Record<string, unknown>);
                      if (!scopeId) return null;
                      const label =
                        (typeof scope.fullName === "string" && scope.fullName) ||
                        (typeof scope.name === "string" && scope.name) ||
                        scopeId;
                      return (
                        <label key={scopeId} className="flex items-center gap-2 text-foreground">
                          <input
                            type="checkbox"
                            checked={selectedScopeIds.has(scopeId)}
                            onChange={(event) => {
                              const next = new Set(selectedScopeIds);
                              if (event.target.checked) next.add(scopeId);
                              else next.delete(scopeId);
                              setSelectedScopeIds(next);
                            }}
                            className="h-4 w-4 rounded border-border text-primary"
                          />
                          <span>{label}</span>
                        </label>
                      );
                    })}
                </div>
                <div className="flex">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void loadPreviewScopes()}
                    disabled={pending || loadingScopes}
                  >
                    {dict.gitProviders.devlake.validate}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Button type="submit" disabled={pending}>
          {pending
            ? dict.gitProviders.form.saving
            : isEdit
              ? dict.gitProviders.form.update
              : dict.gitProviders.form.create}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push(`/${lang}/git-providers`)}
          disabled={pending}
        >
          {dict.gitProviders.form.cancel}
        </Button>
      </div>
    </form>
  );
}
