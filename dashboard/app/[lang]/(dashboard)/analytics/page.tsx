export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import { BarChart3 } from "lucide-react";
import { hasLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/app/dictionaries";
import { GrafanaEmbed } from "@/components/analytics";

export default async function AnalyticsPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const grafanaUrl = process.env.NEXT_PUBLIC_DEVLAKE_GRAFANA_URL;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          {dict.analytics.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.analytics.description}
        </p>
      </div>

      {grafanaUrl ? (
        <GrafanaEmbed url={grafanaUrl} />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-10 text-center">
          <BarChart3 className="size-10 text-muted-foreground" />
          <h3 className="mt-3 text-lg font-medium text-foreground">
            {dict.analytics.notConfigured.title}
          </h3>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            {dict.analytics.notConfigured.description}
          </p>
          <code className="mt-4 rounded bg-muted px-3 py-1.5 text-xs text-muted-foreground">
            {dict.analytics.notConfigured.hint}
          </code>
        </div>
      )}
    </div>
  );
}
