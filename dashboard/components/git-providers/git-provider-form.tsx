"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
  createGitProvider,
  updateGitProvider,
} from "@/lib/actions/git-providers";
import type { GitProviderType } from "@/generated/prisma/client";

interface GitProviderFormProps {
  provider?: {
    id: string;
    type: GitProviderType;
    name: string;
    baseUrl: string | null;
    webhookSecret: string | null;
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

  const showBaseUrl = selfHostedProviders.includes(selectedType);

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
        <Label htmlFor="type">{dict.gitProviders.form.type}</Label>
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
        <Label htmlFor="name">{dict.gitProviders.form.name}</Label>
        <Input
          id="name"
          name="name"
          defaultValue={provider?.name}
          placeholder={dict.gitProviders.form.namePlaceholder}
          aria-invalid={!!errors.name}
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
          <Label htmlFor="baseUrl">{dict.gitProviders.form.baseUrl}</Label>
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

      <div className="space-y-2">
        <Label htmlFor="accessToken">
          {dict.gitProviders.form.accessToken}
        </Label>
        <Input
          id="accessToken"
          name="accessToken"
          type="password"
          placeholder={
            isEdit
              ? dict.gitProviders.form.accessTokenPlaceholderEdit
              : dict.gitProviders.form.accessTokenPlaceholder
          }
          required={!isEdit}
          aria-invalid={!!errors.accessToken}
        />
        {errors.accessToken && (
          <p className="text-sm text-destructive">{errors.accessToken}</p>
        )}
        <p className="text-sm text-muted-foreground">
          {dict.gitProviders.form.accessTokenHelp}
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="webhookSecret">
          {dict.gitProviders.form.webhookSecret}
        </Label>
        <Input
          id="webhookSecret"
          name="webhookSecret"
          type="password"
          defaultValue={provider?.webhookSecret ?? ""}
          placeholder={dict.gitProviders.form.webhookSecretPlaceholder}
          aria-invalid={!!errors.webhookSecret}
        />
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
