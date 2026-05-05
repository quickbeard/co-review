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

type GrafanaProvider = "github" | "gitlab" | "azure_devops";

const GRAFANA_PROVIDERS: readonly GrafanaProvider[] = [
  "github",
  "gitlab",
  "azure_devops",
];

function parseDashboardUidMap(
  rawMap: string | undefined,
): Partial<Record<GrafanaProvider, string>> {
  if (!rawMap) return {};

  return rawMap
    .split(",")
    .map((pair) => pair.trim())
    .filter(Boolean)
    .reduce<Partial<Record<GrafanaProvider, string>>>((acc, pair) => {
      const [rawKey, rawUid] = pair.split(":");
      if (!rawKey || !rawUid) return acc;
      const key = rawKey.trim().toLowerCase() as GrafanaProvider;
      const uid = rawUid.trim();
      if (!GRAFANA_PROVIDERS.includes(key) || uid.length === 0) return acc;
      acc[key] = uid;
      return acc;
    }, {});
}

function buildGrafanaDashboardUrl(
  baseUrl: string,
  uid: string,
  provider: GrafanaProvider,
): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${normalizedBase}/d/${uid}/co-review-${provider}`);
  url.searchParams.set("orgId", "1");
  url.searchParams.set("kiosk", "");
  url.searchParams.set("theme", "light");
  return url.toString();
}

function appendRepoFilters(url: string, names: string[]): string {
  if (names.length === 0) return url;
  const parsed = new URL(url);
  parsed.searchParams.delete("var-repo");
  for (const name of names) {
    parsed.searchParams.append("var-repo", name);
  }
  return parsed.toString();
}

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
  const grafanaBaseUrl = process.env.NEXT_PUBLIC_DEVLAKE_GRAFANA_BASE_URL;
  const dashboardUidMap = parseDashboardUidMap(
    process.env.NEXT_PUBLIC_DEVLAKE_GRAFANA_DASHBOARD_UID_MAP,
  );
  const legacyGrafanaUrl = process.env.NEXT_PUBLIC_DEVLAKE_GRAFANA_URL || null;

  const providerUrls: Partial<Record<GrafanaProvider, string>> = {};
  for (const provider of GRAFANA_PROVIDERS) {
    const uid = dashboardUidMap[provider];
    if (grafanaBaseUrl && uid) {
      providerUrls[provider] = buildGrafanaDashboardUrl(
        grafanaBaseUrl,
        uid,
        provider,
      );
    }
  }
  if (Object.keys(providerUrls).length === 0 && legacyGrafanaUrl) {
    providerUrls.github = legacyGrafanaUrl;
  }

  const providersResult = await getGitProviders();
  const activeProvider = providersResult.success
    ? providersResult.data?.find((p) => p.isActive)
    : undefined;
  const defaultProvider = GRAFANA_PROVIDERS.includes(
    activeProvider?.type as GrafanaProvider,
  )
    ? (activeProvider?.type as GrafanaProvider)
    : "github";

  const providerRecordByType = new Map<GrafanaProvider, number>();
  if (providersResult.success && providersResult.data?.length) {
    for (const providerType of GRAFANA_PROVIDERS) {
      const matched = providersResult.data
        .filter((provider) => provider.type === providerType)
        .sort((a, b) => Number(b.isActive) - Number(a.isActive))[0];
      if (matched) providerRecordByType.set(providerType, matched.id);
    }
  }

  const integrations = await Promise.all(
    GRAFANA_PROVIDERS.map(async (providerType) => {
      const providerId = providerRecordByType.get(providerType);
      if (!providerId) {
        return { providerType, repoNames: [] as string[] };
      }

      const integrationResult = await getDevLakeIntegration(providerId);
      if (
        !integrationResult.success ||
        !integrationResult.data?.enabled ||
        integrationResult.data.selectedScopes.length === 0
      ) {
        return { providerType, repoNames: [] as string[] };
      }

      const repoNames = integrationResult.data.selectedScopes
        .map((scope) => {
          const record = scope as Record<string, unknown>;
          return (
            (typeof record.fullName === "string" && record.fullName) ||
            (typeof record.name === "string" && record.name) ||
            null
          );
        })
        .filter((name): name is string => !!name);

      return { providerType, repoNames };
    }),
  );

  for (const { providerType, repoNames } of integrations) {
    const currentUrl = providerUrls[providerType];
    if (!currentUrl || repoNames.length === 0) continue;
    providerUrls[providerType] = appendRepoFilters(currentUrl, repoNames);
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

      {Object.keys(providerUrls).length > 0 ? (
        <GrafanaEmbed urls={providerUrls} defaultProvider={defaultProvider} />
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
