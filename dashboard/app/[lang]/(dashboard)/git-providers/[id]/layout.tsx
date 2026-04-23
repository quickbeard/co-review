export const dynamic = "force-dynamic";

// Shared shell for every per-provider sub-page:
//   /git-providers/{id}/edit         - "Credentials" tab
//   /git-providers/{id}/webhooks/..  - "Repository Webhooks" tab
//
// We fetch the provider once here so each tab can render its own payload
// without re-running the provider query. The webhook count is fetched here
// too because it's cheap (a filtered list) and drives the tab-strip badge.

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { notFound } from "next/navigation";

import { ProviderTabsNav } from "@/components/git-providers";
import { ProviderTypeBadge } from "@/components/git-providers";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { getGitProvider } from "@/lib/api/git-providers";
import { getWebhooks } from "@/lib/api/webhooks";

interface LayoutProps {
  children: React.ReactNode;
  params: Promise<{ lang: string; id: string }>;
}

export default async function GitProviderDetailLayout({
  children,
  params,
}: LayoutProps) {
  const { lang, id } = await params;
  if (!hasLocale(lang)) notFound();

  const dict = await getDictionary(lang);
  const providerResult = await getGitProvider(id);
  if (!providerResult.success || !providerResult.data) {
    notFound();
  }

  const provider = providerResult.data;

  // Best-effort; a failure here must never block the edit form. We default
  // to undefined so the tab badge is simply hidden when the API is down.
  const webhooksResult = await getWebhooks({ gitProviderId: provider.id });
  const webhookCount =
    webhooksResult.success && webhooksResult.data
      ? webhooksResult.data.length
      : undefined;

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/${lang}/git-providers`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          {dict.gitProviders.backToList}
        </Link>
        <div className="mt-4 flex items-center gap-3">
          <h1 className="text-2xl font-bold text-foreground">
            {provider.name}
          </h1>
          <ProviderTypeBadge type={provider.type} />
        </div>
        <p className="mt-1 text-muted-foreground">
          {dict.gitProviders.editProvider.description}
        </p>
      </div>

      <ProviderTabsNav
        lang={lang}
        providerId={provider.id}
        webhookCount={webhookCount}
      />

      {children}
    </div>
  );
}
