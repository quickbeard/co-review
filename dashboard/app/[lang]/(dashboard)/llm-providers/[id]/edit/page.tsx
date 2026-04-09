export const dynamic = "force-dynamic";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { LLMProviderForm } from "@/components/llm-providers";
import { getLLMProvider } from "@/lib/api/llm-providers";

export default async function EditLLMProviderPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const result = await getLLMProvider(id);

  if (!result.success || !result.data) {
    notFound();
  }

  const provider = result.data;

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
          {dict.llmProviders.editProvider.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.llmProviders.editProvider.description}
        </p>
      </div>

      <div className="max-w-xl rounded-lg border border-border bg-background p-6">
        <LLMProviderForm provider={provider} lang={lang} />
      </div>
    </div>
  );
}
