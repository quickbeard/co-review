export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import { BarChart3 } from "lucide-react";
import { hasLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/app/dictionaries";
import { GrafanaEmbed } from "@/components/analytics";
import {
  getDevLakeIntegration,
  getGitProviders,
} from "@/lib/api/git-providers";

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
  const grafanaBaseUrl = process.env.NEXT_PUBLIC_DEVLAKE_GRAFANA_URL;
  let grafanaUrl = grafanaBaseUrl || null;

  if (grafanaBaseUrl) {
    const providersResult = await getGitProviders();
    if (providersResult.success && providersResult.data?.length) {
      const activeProvider = providersResult.data.find((p) => p.isActive);
      if (activeProvider) {
        const integrationResult = await getDevLakeIntegration(activeProvider.id);
        if (
          integrationResult.success &&
          integrationResult.data?.enabled &&
          integrationResult.data.selectedScopes.length > 0
        ) {
          const parsed = new URL(grafanaBaseUrl);
          const names = integrationResult.data.selectedScopes
            .map((scope) => {
              const record = scope as Record<string, unknown>;
              return (
                (typeof record.fullName === "string" && record.fullName) ||
                (typeof record.name === "string" && record.name) ||
                null
              );
            })
            .filter((name): name is string => !!name);
          if (names.length > 0) {
            parsed.searchParams.delete("var-repo");
            for (const name of names) {
              parsed.searchParams.append("var-repo", name);
            }
            grafanaUrl = parsed.toString();
          }
        }
      }
    }
  }

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
