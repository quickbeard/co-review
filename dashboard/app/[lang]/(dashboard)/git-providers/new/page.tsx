export const dynamic = "force-dynamic";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { GitProviderForm } from "@/components/git-providers";

export default async function NewGitProviderPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);

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
        <h1 className="mt-4 text-2xl font-bold text-foreground">
          {dict.gitProviders.newProvider.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.gitProviders.newProvider.description}
        </p>
      </div>

      <div className="max-w-xl rounded-lg border border-border bg-background p-6">
        <GitProviderForm lang={lang} />
      </div>
    </div>
  );
}
