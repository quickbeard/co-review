export const dynamic = "force-dynamic";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LLMProviderList } from "@/components/llm-providers";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { getLLMProviders } from "@/lib/api/llm-providers";

export default async function LLMProvidersPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const result = await getLLMProviders();
  const providers = result.success ? (result.data ?? []) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {dict.llmProviders.title}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {dict.llmProviders.description}
          </p>
        </div>
        <Link href={`/${lang}/llm-providers/new`}>
          <Button className="flex items-center gap-2">
            <Plus className="size-4" />
            {dict.llmProviders.addProvider}
          </Button>
        </Link>
      </div>

      {!result.success && (
        <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-4 text-sm text-yellow-700 dark:text-yellow-400">
          {dict.llmProviders.apiError}: {result.error}
        </div>
      )}

      <LLMProviderList providers={providers} lang={lang} />
    </div>
  );
}
