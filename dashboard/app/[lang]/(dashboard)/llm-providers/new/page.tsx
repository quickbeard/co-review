export const dynamic = "force-dynamic";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { LLMProviderForm } from "@/components/llm-providers";
import { getTokenLimits } from "@/lib/api/token-limits";

export default async function NewLLMProviderPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const tokenLimitsResult = await getTokenLimits();
  const tokenLimits = tokenLimitsResult.success ? tokenLimitsResult.data : null;

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/${lang}/llm-providers`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          {dict.llmProviders.backToList}
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-foreground">
          {dict.llmProviders.newProvider.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.llmProviders.newProvider.description}
        </p>
      </div>

      <div className="max-w-2xl rounded-lg border border-border bg-background p-6">
        <LLMProviderForm
          lang={lang}
          tokenLimits={
            tokenLimits ?? {
              max_description_tokens: 500,
              max_commits_tokens: 500,
              max_model_tokens: 32000,
              custom_model_max_tokens: 32000,
            }
          }
        />
      </div>
    </div>
  );
}
