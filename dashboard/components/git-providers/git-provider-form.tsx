"use client";

import { useState } from "react";
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
  updateGitProvider,
} from "@/lib/actions/git-providers";
import type {
  GitProviderType,
  GitHubDeploymentType,
} from "@/generated/prisma/client";

interface GitProviderFormProps {
  provider?: {
    id: string;
    type: GitProviderType;
    name: string;
    baseUrl: string | null;
    webhookSecret: string | null;
    deploymentType: GitHubDeploymentType | null;
    appId: string | null;
  };
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

  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<GitProviderType>(
    provider?.type ?? "github",
  );
  const [deploymentType, setDeploymentType] = useState<GitHubDeploymentType>(
    provider?.deploymentType ?? "user",
  );
  const [showAccessToken, setShowAccessToken] = useState(false);
  const [showWebhookSecret, setShowWebhookSecret] = useState(false);

  const showBaseUrl = selfHostedProviders.includes(selectedType);
  const isGitHub = selectedType === "github";

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrors({});
    setError(null);
    setPending(true);

    const formData = new FormData(e.currentTarget);

    try {
      const result = isEdit
        ? await updateGitProvider(formData)
        : await createGitProvider(formData);

      if (!result.success) {
        setError(result.error);
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
    <form onSubmit={handleSubmit} className="space-y-6">
      {isEdit && <input type="hidden" name="id" value={provider.id} />}

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

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
            <SelectValue placeholder={dict.gitProviders.form.selectType} />
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
          aria-invalid={!!errors.name}
          required
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name}</p>
        )}
        <p className="text-sm text-muted-foreground">
          {dict.gitProviders.form.nameHelp}
        </p>
      </div>

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

      {/* GitHub Deployment Type Radio Buttons */}
      {isGitHub && (
        <div className="space-y-3">
          <Label>
            {dict.gitProviders.form.deploymentType}
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <div className="flex gap-6">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="deploymentType"
                value="user"
                checked={deploymentType === "user"}
                onChange={(e) =>
                  setDeploymentType(e.target.value as GitHubDeploymentType)
                }
                className="h-4 w-4 border-input text-primary focus:ring-ring"
              />
              <span className="text-sm">
                {dict.gitProviders.form.deploymentTypeUser}
              </span>
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="deploymentType"
                value="app"
                checked={deploymentType === "app"}
                onChange={(e) =>
                  setDeploymentType(e.target.value as GitHubDeploymentType)
                }
                className="h-4 w-4 border-input text-primary focus:ring-ring"
              />
              <span className="text-sm">
                {dict.gitProviders.form.deploymentTypeApp}
              </span>
            </label>
          </div>
          {errors.deploymentType && (
            <p className="text-sm text-destructive">{errors.deploymentType}</p>
          )}
          <p className="text-sm text-muted-foreground">
            {dict.gitProviders.form.deploymentTypeHelp}
          </p>
        </div>
      )}

      {/* Personal Access Token - for non-GitHub or GitHub user deployment */}
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
                  : isGitHub
                    ? dict.gitProviders.form.userTokenPlaceholder
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

      {/* GitHub App Fields */}
      {isGitHub && deploymentType === "app" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="appId">
              {dict.gitProviders.form.appId}
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <Input
              id="appId"
              name="appId"
              defaultValue={provider?.appId ?? ""}
              placeholder={dict.gitProviders.form.appIdPlaceholder}
              required={!isEdit}
              aria-invalid={!!errors.appId}
            />
            {errors.appId && (
              <p className="text-sm text-destructive">{errors.appId}</p>
            )}
            <p className="text-sm text-muted-foreground">
              {dict.gitProviders.form.appIdHelp}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="privateKey">
              {dict.gitProviders.form.privateKey}
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <Textarea
              id="privateKey"
              name="privateKey"
              placeholder={
                isEdit
                  ? dict.gitProviders.form.privateKeyPlaceholderEdit
                  : dict.gitProviders.form.privateKeyPlaceholder
              }
              required={!isEdit}
              aria-invalid={!!errors.privateKey}
              rows={6}
              className="font-mono text-xs"
            />
            {errors.privateKey && (
              <p className="text-sm text-destructive">{errors.privateKey}</p>
            )}
            <p className="text-sm text-muted-foreground">
              {dict.gitProviders.form.privateKeyHelp}
            </p>
          </div>
        </>
      )}

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
            defaultValue={provider?.webhookSecret ?? ""}
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
