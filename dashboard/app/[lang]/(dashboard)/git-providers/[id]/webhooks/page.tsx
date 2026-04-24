export const dynamic = "force-dynamic";

// "Repository Webhooks" tab under /git-providers/{id}/. Lists registrations
// scoped to this provider only and (for GitHub PAT mode) lets users add and
// manage them inline. For modes that don't need per-repo webhooks (GitHub
// App) or providers whose adapter is not wired yet, we explain the state
// so the operator understands why no "Add" button is available.

import Link from "next/link";
import { Plus } from "lucide-react";
import { notFound } from "next/navigation";

import { Button } from "@/components/ui/button";
import { WebhookList } from "@/components/webhooks";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { getGitProvider } from "@/lib/api/git-providers";
import { getGitProviders } from "@/lib/api/git-providers";
import { getWebhooks } from "@/lib/api/webhooks";

// Provider types whose adapter is implemented end-to-end today. Everything
// else is allowed to list existing rows (so users can delete stragglers)
// but registration through the UI is hidden until the adapter ships.
const SUPPORTS_UI_REGISTRATION = new Set(["github"]);

export default async function ProviderWebhooksTab({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  if (!hasLocale(lang)) notFound();

  const dict = await getDictionary(lang);

  const providerResult = await getGitProvider(id);
  if (!providerResult.success || !providerResult.data) notFound();
  const provider = providerResult.data;

  const providerIdNumber = provider.id;

  const [webhooksResult, providersResult] = await Promise.all([
    getWebhooks({ gitProviderId: providerIdNumber }),
    getGitProviders(),
  ]);

  const webhooks = webhooksResult.success ? (webhooksResult.data ?? []) : [];
  const allProviders = providersResult.success
    ? (providersResult.data ?? [])
    : [];

  const providerSupported = SUPPORTS_UI_REGISTRATION.has(provider.type);
  // GitHub App installations receive deliveries at the App's own URL, so
  // per-repo webhook registration through this UI is deliberately disabled
  // server-side (see pr_agent/servers/webhook_registry.py::_github_client).
  const appMode =
    provider.type === "github" && provider.deploymentType === "app";
  const canAdd = providerSupported && !appMode;

  const webhooksBase = `/${lang}/git-providers/${providerIdNumber}/webhooks`;
  const addHref = `${webhooksBase}/new`;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            {dict.gitProviders.webhooksTab.title}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {dict.gitProviders.webhooksTab.description}
          </p>
        </div>
        {canAdd && (
          <Link href={addHref}>
            <Button className="flex items-center gap-2">
              <Plus className="size-4" />
              {dict.webhooks.addWebhook}
            </Button>
          </Link>
        )}
      </div>

      {appMode && (
        <div className="rounded-md border border-blue-500/40 bg-blue-500/10 p-4 text-sm text-blue-700 dark:text-blue-300">
          {dict.gitProviders.webhooksTab.appModeBanner}
        </div>
      )}

      {!providerSupported && (
        <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-4 text-sm text-yellow-700 dark:text-yellow-400">
          {dict.gitProviders.webhooksTab.unsupportedProvider}
        </div>
      )}

      {!webhooksResult.success && (
        <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-4 text-sm text-yellow-700 dark:text-yellow-400">
          {dict.webhooks.errors.apiError}: {webhooksResult.error}
        </div>
      )}

      <WebhookList
        webhooks={webhooks}
        providers={allProviders}
        lang={lang}
        hideProviderColumn
        addHref={addHref}
        editHrefBase={webhooksBase}
      />
    </div>
  );
}
