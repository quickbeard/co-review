export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { hasLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/app/dictionaries";
import { getAutomationConfig } from "@/lib/api/automation";
import { AutomationForm } from "@/components/automation";

export default async function AutomationPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const result = await getAutomationConfig();

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
          {dict.automation.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.automation.description}
        </p>
      </div>

      {result.success && result.data ? (
        <AutomationForm initial={result.data} />
      ) : (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {result.error ?? dict.automation.errors.loadFailed}
        </div>
      )}
    </div>
  );
}
