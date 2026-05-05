"use client";

import { useMemo, useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDictionary } from "@/lib/i18n/dictionary-context";

type GrafanaProvider = "github" | "gitlab" | "azure_devops";

interface GrafanaEmbedProps {
  urls: Partial<Record<GrafanaProvider, string>>;
  defaultProvider: GrafanaProvider;
}

/**
 * Embeds a Grafana dashboard via an iframe.
 *
 * The parent Grafana instance MUST have `allow_embedding = true` in its
 * grafana.ini (security section). Anonymous access or an Organization API
 * token is typically also needed. See README/guide in the Analytics page.
 */
export function GrafanaEmbed({ urls, defaultProvider }: GrafanaEmbedProps) {
  const dict = useDictionary();
  const [nonce, setNonce] = useState(0);
  const [provider, setProvider] = useState<GrafanaProvider>(defaultProvider);
  const selectedUrl = urls[provider] ?? null;

  const providerOptions: { value: GrafanaProvider; label: string }[] = [
    { value: "github", label: dict.analytics.providers.github },
    { value: "gitlab", label: dict.analytics.providers.gitlab },
    { value: "azure_devops", label: dict.analytics.providers.azureDevops },
  ];

  const iframeSrc = useMemo(() => {
    if (!selectedUrl) return null;
    // Append a cache-busting param when the user hits refresh so the iframe
    // reloads. Preserves the existing query string intact.
    if (nonce === 0) return selectedUrl;
    const sep = selectedUrl.includes("?") ? "&" : "?";
    return `${selectedUrl}${sep}_refresh=${nonce}`;
  }, [selectedUrl, nonce]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:w-64">
          <Select
            value={provider}
            onValueChange={(value) => setProvider(value as GrafanaProvider)}
          >
            <SelectTrigger aria-label={dict.analytics.providerLabel}>
              <SelectValue placeholder={dict.analytics.providerPlaceholder}>
                {(value) =>
                  providerOptions.find((option) => option.value === value)
                    ?.label ?? value
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {providerOptions.map((option) => (
                <SelectItem
                  key={option.value}
                  value={option.value}
                  disabled={!urls[option.value]}
                >
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setNonce(Date.now())}
            disabled={!selectedUrl}
            className="gap-2"
          >
            <RefreshCw className="size-4" />
            {dict.analytics.refresh}
          </Button>
          {selectedUrl && (
            <a
              href={selectedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex"
            >
              <Button variant="outline" size="sm" className="gap-2">
                <ExternalLink className="size-4" />
                {dict.analytics.openInGrafana}
              </Button>
            </a>
          )}
        </div>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-border bg-background">
        {iframeSrc ? (
          <iframe
            key={iframeSrc}
            src={iframeSrc}
            title="Apache DevLake — Grafana"
            className="h-[80vh] w-full"
            // Grafana needs these to render its charts when embedded.
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
            loading="lazy"
          />
        ) : (
          <div className="flex h-[80vh] items-center justify-center px-6 text-center text-sm text-muted-foreground">
            {dict.analytics.providerNotConfigured}
          </div>
        )}
      </div>
    </div>
  );
}
