export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import { hasLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/app/dictionaries";
import { getLearnings } from "@/lib/api/learnings";
import { LearningsView } from "@/components/learnings";

export default async function LearningsPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const result = await getLearnings({ limit: 100 });

  const initial = result.success ? (result.data ?? null) : null;
  const initialError = result.success ? null : (result.error ?? null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          {dict.learnings.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.learnings.description}
        </p>
      </div>

      <LearningsView initial={initial} initialError={initialError} />
    </div>
  );
}
