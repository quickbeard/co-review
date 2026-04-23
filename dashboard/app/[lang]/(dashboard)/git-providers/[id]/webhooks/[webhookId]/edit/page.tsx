export const dynamic = "force-dynamic";

// Edit a webhook registration scoped to a specific provider. We guard
// against cross-provider deep-links by asserting the webhook's provider id
// matches the URL segment; mismatches redirect back to the correct
// provider's tab so users never end up editing a webhook under the wrong
// provider's header.

import { notFound, redirect } from "next/navigation";

import { WebhookForm } from "@/components/webhooks";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { getGitProvider, getGitProviders } from "@/lib/api/git-providers";
import { getWebhook } from "@/lib/api/webhooks";

export default async function EditProviderWebhookPage({
  params,
}: {
  params: Promise<{ lang: string; id: string; webhookId: string }>;
}) {
  const { lang, id, webhookId } = await params;
  if (!hasLocale(lang)) notFound();

  const dict = await getDictionary(lang);

  const [providerResult, webhookResult, providersResult] = await Promise.all([
    getGitProvider(id),
    getWebhook(webhookId),
    getGitProviders(),
  ]);

  if (!providerResult.success || !providerResult.data) notFound();
  if (!webhookResult.success || !webhookResult.data) notFound();

  const provider = providerResult.data;
  const webhook = webhookResult.data;

  // Guard: if the URL lies about which provider owns this webhook, redirect
  // to the canonical URL rather than silently rendering under the wrong
  // header.
  if (webhook.git_provider_id !== provider.id) {
    redirect(
      `/${lang}/git-providers/${webhook.git_provider_id}/webhooks/${webhook.id}/edit`,
    );
  }

  const providers = providersResult.success
    ? (providersResult.data ?? [])
    : [];

  const returnHref = `/${lang}/git-providers/${provider.id}/webhooks`;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">
          {dict.webhooks.editTitle}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {dict.webhooks.editDescription}
        </p>
      </div>

      <WebhookForm
        lang={lang}
        providers={providers}
        initial={webhook}
        mode="edit"
        lockedProviderId={provider.id}
        returnHref={returnHref}
      />
    </div>
  );
}
