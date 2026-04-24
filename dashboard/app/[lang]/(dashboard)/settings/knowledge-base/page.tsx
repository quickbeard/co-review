export const dynamic = "force-dynamic";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { notFound } from "next/navigation";

import { hasLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/app/dictionaries";
import { getKnowledgeBaseConfig } from "@/lib/api/knowledge-base";
import { KnowledgeBaseForm } from "@/components/settings/knowledge-base";

export default async function KnowledgeBaseSettingsPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const result = await getKnowledgeBaseConfig();

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/${lang}/settings`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-4" />
          {dict.settings.backToSettings}
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">
          {dict.knowledgeBase.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.knowledgeBase.description}
        </p>
      </div>

      {result.success && result.data ? (
        <KnowledgeBaseForm initial={result.data} />
      ) : (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {result.error ?? dict.knowledgeBase.errors.loadFailed}
        </div>
      )}
    </div>
  );
}
