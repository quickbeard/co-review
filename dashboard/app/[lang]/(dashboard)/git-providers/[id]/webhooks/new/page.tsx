export const dynamic = "force-dynamic";

// New webhook form scoped to a single provider. The provider selector is
// hidden because the provider is already implied by the URL, and Save
// returns the user to the provider's Webhooks tab.

import { notFound } from "next/navigation";

import { WebhookForm } from "@/components/webhooks";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { getGitProvider, getGitProviders } from "@/lib/api/git-providers";

export default async function NewProviderWebhookPage({
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

  // We still fetch all providers because the shared form expects the list
  // for disabled/fallback branches; only the currently-scoped one will be
  // shown in the locked mode below.
  const providersResult = await getGitProviders();
  const providers = providersResult.success
    ? (providersResult.data ?? [])
    : [];

  const returnHref = `/${lang}/git-providers/${provider.id}/webhooks`;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">
          {dict.webhooks.newTitle}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {dict.webhooks.newDescription}
        </p>
      </div>

      <WebhookForm
        lang={lang}
        providers={providers}
        mode="create"
        lockedProviderId={provider.id}
        returnHref={returnHref}
      />
    </div>
  );
}
