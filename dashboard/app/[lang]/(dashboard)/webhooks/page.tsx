export const dynamic = "force-dynamic";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { WebhookList } from "@/components/webhooks";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { getWebhooks } from "@/lib/api/webhooks";
import { getGitProviders } from "@/lib/api/git-providers";

export default async function WebhooksPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();

  const dict = await getDictionary(lang);

  // Run both requests in parallel so the list renders as fast as whichever
  // one is slower; failures degrade gracefully via the defensive defaults
  // returned below.
  const [webhooksResult, providersResult] = await Promise.all([
    getWebhooks(),
    getGitProviders(),
  ]);

  const webhooks = webhooksResult.success ? (webhooksResult.data ?? []) : [];
  const providers = providersResult.success
    ? (providersResult.data ?? [])
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {dict.webhooks.title}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {dict.webhooks.description}
          </p>
        </div>
        <Link href={`/${lang}/webhooks/new`}>
          <Button className="flex items-center gap-2">
            <Plus className="size-4" />
            {dict.webhooks.addWebhook}
          </Button>
        </Link>
      </div>

      {!webhooksResult.success && (
        <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-4 text-sm text-yellow-700 dark:text-yellow-400">
          {dict.webhooks.errors.apiError}: {webhooksResult.error}
        </div>
      )}

      <WebhookList
        webhooks={webhooks}
        providers={providers}
        lang={lang}
      />
    </div>
  );
}
