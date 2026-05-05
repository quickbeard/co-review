export const dynamic = "force-dynamic";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GitProviderList } from "@/components/git-providers";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { getGitProviders } from "@/lib/api/git-providers";
import { getWebhooks } from "@/lib/api/webhooks";

export default async function GitProvidersPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);

  // Load providers and all webhook rows in parallel. The webhook list is
  // small (one row per repo per provider) so a single query + client-side
  // tally is simpler than N per-provider queries.
  const [providersResult, webhooksResult] = await Promise.all([
    getGitProviders(),
    getWebhooks(),
  ]);

  const providers = providersResult.success
    ? (providersResult.data ?? [])
    : [];

  const webhookCounts: Record<number, number> = {};
  if (webhooksResult.success && webhooksResult.data) {
    for (const w of webhooksResult.data) {
      webhookCounts[w.git_provider_id] =
        (webhookCounts[w.git_provider_id] ?? 0) + 1;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {dict.gitProviders.title}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {dict.gitProviders.description}
          </p>
        </div>
        <Link href={`/${lang}/git-providers/new`}>
          <Button className="flex items-center gap-2">
            <Plus className="size-4" />
            {dict.gitProviders.addProvider}
          </Button>
        </Link>
      </div>

      {!providersResult.success && (
        <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-4 text-sm text-yellow-700 dark:text-yellow-400">
          {dict.gitProviders.apiError}: {providersResult.error}
        </div>
      )}

      <GitProviderList
        providers={providers}
        lang={lang}
        webhookCounts={webhookCounts}
      />
    </div>
  );
}
