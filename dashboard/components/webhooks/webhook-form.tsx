"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCcw, Save } from "lucide-react";
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
import { StringListEditor } from "@/components/automation/string-list-editor";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import type { GitProvider } from "@/lib/api/types";
import {
  createWebhook,
  getWebhookEndpoints,
  updateWebhook,
  type WebhookEndpointInfo,
  type WebhookRegistration,
} from "@/lib/api/webhooks";

interface WebhookFormProps {
  lang: string;
  providers: GitProvider[];
  initial?: WebhookRegistration;
  mode: "create" | "edit";
  // When set, the provider selector is hidden and the form operates as if
  // this provider was the only choice. Used by the per-provider webhooks
  // tab where the provider is implied by the route.
  lockedProviderId?: number;
  // Where to send the user on save/cancel. Defaults to the top-level
  // /webhooks list to preserve existing behaviour when omitted.
  returnHref?: string;
}

// Event presets per provider type. Mirrors the defaults the backend advertises
// via GET /api/webhooks/endpoints; kept in sync there for initial population.
const EVENT_PRESETS: Record<string, string[]> = {
  github: ["push", "pull_request", "issue_comment", "pull_request_review"],
  gitlab: ["push_events", "merge_requests_events", "note_events"],
  bitbucket: ["pullrequest:created", "pullrequest:updated", "pullrequest:fulfilled"],
  bitbucket_server: ["pr:opened", "pr:modified", "pr:merged", "pr:comment:added"],
  gitea: ["pull_request", "push", "issues"],
  azure_devops: ["git.pullrequest.created", "git.pullrequest.updated"],
};

export function WebhookForm({
  lang,
  providers,
  initial,
  mode,
  lockedProviderId,
  returnHref,
}: WebhookFormProps) {
  const dict = useDictionary();
  const router = useRouter();

  // Where the Cancel button and successful save redirect to. Nested
  // (per-provider) callers pass a provider-scoped path; the standalone
  // /webhooks route keeps the previous behaviour.
  const defaultReturnHref = `/${lang}/webhooks`;
  const navigateHome = returnHref ?? defaultReturnHref;

  // Filter to providers that are active AND whose type is supported by at
  // least one adapter (the backend will reject unsupported ones with 501;
  // we still show them so the user can at least stash a draft row).
  const selectableProviders = useMemo(
    () => providers.filter((p) => p.isActive),
    [providers],
  );

  const [providerId, setProviderId] = useState<number | "">(
    lockedProviderId ??
      initial?.git_provider_id ??
      selectableProviders[0]?.id ??
      "",
  );
  const [repo, setRepo] = useState(initial?.repo ?? "");
  const [targetUrl, setTargetUrl] = useState(initial?.target_url ?? "");
  const [events, setEvents] = useState<string[]>(initial?.events ?? []);
  const [active, setActive] = useState<boolean>(initial?.active ?? true);
  const [contentType, setContentType] = useState<string>(
    initial?.content_type ?? "json",
  );
  const [insecureSsl, setInsecureSsl] = useState<boolean>(
    initial?.insecure_ssl ?? false,
  );
  const [secret, setSecret] = useState<string>("");
  const [endpoints, setEndpoints] = useState<WebhookEndpointInfo[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Load endpoint suggestions once so the "Use suggested URL" button has
    // something to offer. Failure here is non-fatal; users can type the URL.
    getWebhookEndpoints().then((r) => {
      if (r.success && r.data) setEndpoints(r.data);
    });
  }, []);

  const selectedProvider =
    providerId === ""
      ? undefined
      : providers.find((p) => p.id === providerId);

  const providerTypeKey = selectedProvider?.type ?? "";
  const eventPresets = EVENT_PRESETS[providerTypeKey] ?? [];

  const suggestedEndpoint = endpoints.find(
    (e) => e.provider_type === providerTypeKey,
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (providerId === "") {
      alert(dict.webhooks.errors.providerRequired);
      return;
    }
    setSaving(true);
    try {
      if (mode === "create") {
        const result = await createWebhook({
          git_provider_id: Number(providerId),
          repo: repo.trim(),
          target_url: targetUrl.trim(),
          events: events.length > 0 ? events : null,
          active,
          content_type: contentType,
          insecure_ssl: insecureSsl,
          secret: secret.trim() || null,
        });
        if (!result.success) {
          alert(result.error || dict.webhooks.errors.saveFailed);
          return;
        }
        router.push(navigateHome);
        router.refresh();
      } else if (initial) {
        const result = await updateWebhook(initial.id, {
          repo: repo.trim(),
          target_url: targetUrl.trim(),
          events: events.length > 0 ? events : null,
          active,
          content_type: contentType,
          insecure_ssl: insecureSsl,
          // Only send the secret if the user actually typed one (blank =
          // "leave as-is"); otherwise we'd clobber the stored secret.
          ...(secret.trim() ? { secret: secret.trim() } : {}),
        });
        if (!result.success) {
          alert(result.error || dict.webhooks.errors.saveFailed);
          return;
        }
        router.push(navigateHome);
        router.refresh();
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div
        className={
          lockedProviderId ? "space-y-2" : "grid gap-4 md:grid-cols-2"
        }
      >
        {!lockedProviderId && (
          <div className="space-y-2">
            <Label htmlFor="provider">{dict.webhooks.form.provider}</Label>
            <Select
              value={providerId === "" ? "" : String(providerId)}
              onValueChange={(v) => setProviderId(v ? Number(v) : "")}
              disabled={mode === "edit"}
            >
              <SelectTrigger id="provider">
                <SelectValue
                  placeholder={dict.webhooks.form.providerPlaceholder}
                />
              </SelectTrigger>
              <SelectContent>
                {selectableProviders.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name} ({p.type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {mode === "edit" && (
              <p className="text-xs text-muted-foreground">
                {dict.webhooks.form.providerLockedNote}
              </p>
            )}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="repo">{dict.webhooks.form.repo}</Label>
          <Input
            id="repo"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder={dict.webhooks.form.repoPlaceholder}
            required
          />
          <p className="text-xs text-muted-foreground">
            {dict.webhooks.form.repoHint}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-end justify-between gap-2">
          <Label htmlFor="url">{dict.webhooks.form.targetUrl}</Label>
          {suggestedEndpoint && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setTargetUrl(suggestedEndpoint.path)}
            >
              <RefreshCcw className="mr-1 h-3 w-3" />
              {dict.webhooks.form.useSuggested}
            </Button>
          )}
        </div>
        <Input
          id="url"
          value={targetUrl}
          onChange={(e) => setTargetUrl(e.target.value)}
          placeholder="https://pr-agent.example.com/api/v1/github_webhooks"
          required
        />
        {suggestedEndpoint?.note && (
          <p className="text-xs text-muted-foreground">
            {suggestedEndpoint.note}
          </p>
        )}
      </div>

      <StringListEditor
        id="events"
        label={dict.webhooks.form.events}
        description={dict.webhooks.form.eventsHint}
        values={events}
        onChange={setEvents}
        placeholder={dict.webhooks.form.eventsPlaceholder}
        presets={eventPresets}
        emptyLabel={dict.webhooks.form.eventsEmpty}
        addLabel={dict.webhooks.form.addEvent}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="content-type">{dict.webhooks.form.contentType}</Label>
          <Select
            value={contentType}
            onValueChange={(v) => setContentType(v ?? "json")}
          >
            <SelectTrigger id="content-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="json">json</SelectItem>
              <SelectItem value="form">form</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="secret">{dict.webhooks.form.secret}</Label>
          <Input
            id="secret"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder={
              mode === "edit" && initial?.has_secret
                ? dict.webhooks.form.secretKeepPlaceholder
                : dict.webhooks.form.secretPlaceholder
            }
            autoComplete="off"
          />
          <p className="text-xs text-muted-foreground">
            {mode === "edit"
              ? dict.webhooks.form.secretHintEdit
              : dict.webhooks.form.secretHintCreate}
          </p>
        </div>
      </div>

      <div className="space-y-3 rounded-md border border-border p-3">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            className="mt-0.5 size-4 accent-primary"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />
          <div>
            <div className="text-sm font-medium">
              {dict.webhooks.form.active}
            </div>
            <div className="text-xs text-muted-foreground">
              {dict.webhooks.form.activeHint}
            </div>
          </div>
        </label>

        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            className="mt-0.5 size-4 accent-primary"
            checked={insecureSsl}
            onChange={(e) => setInsecureSsl(e.target.checked)}
          />
          <div>
            <div className="text-sm font-medium">
              {dict.webhooks.form.insecureSsl}
            </div>
            <div className="text-xs text-muted-foreground">
              {dict.webhooks.form.insecureSslHint}
            </div>
          </div>
        </label>
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
        <Button
          type="button"
          variant="ghost"
          onClick={() => router.push(navigateHome)}
          disabled={saving}
        >
          {dict.webhooks.form.cancel}
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          {mode === "create"
            ? dict.webhooks.form.saveCreate
            : dict.webhooks.form.saveUpdate}
        </Button>
      </div>
    </form>
  );
}
