export const dynamic = "force-dynamic";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { GitProviderForm } from "@/components/git-providers";
import { getGitProvider } from "@/lib/actions/git-providers";

export default async function EditGitProviderPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const provider = await getGitProvider(id);

  if (!provider) {
    notFound();
  }

  // Extract only the fields needed by the form
  const formProvider = {
    id: provider.id,
    type: provider.type,
    name: provider.name,
    baseUrl: provider.baseUrl,
    webhookSecret: provider.webhookSecret,
    deploymentType: provider.deploymentType,
    appId: provider.appId,
  };

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/${lang}/git-providers/${id}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          {dict.gitProviders.backToDetail}
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-foreground">
          {dict.gitProviders.editProvider.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.gitProviders.editProvider.description}
        </p>
      </div>

      <div className="max-w-xl rounded-lg border border-border bg-background p-6">
        <GitProviderForm provider={formProvider} lang={lang} />
      </div>
    </div>
  );
}
