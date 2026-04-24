"use client";

import { useMemo, useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDictionary } from "@/lib/i18n/dictionary-context";

interface GrafanaEmbedProps {
  url: string;
}

/**
 * Embeds a Grafana dashboard via an iframe.
 *
 * The parent Grafana instance MUST have `allow_embedding = true` in its
 * grafana.ini (security section). Anonymous access or an Organization API
 * token is typically also needed. See README/guide in the Analytics page.
 */
export function GrafanaEmbed({ url }: GrafanaEmbedProps) {
  const dict = useDictionary();
  const [nonce, setNonce] = useState(0);

  const iframeSrc = useMemo(() => {
    // Append a cache-busting param when the user hits refresh so the iframe
    // reloads. Preserves the existing query string intact.
    if (nonce === 0) return url;
    const sep = url.includes("?") ? "&" : "?";
    return `${url}${sep}_refresh=${nonce}`;
  }, [url, nonce]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setNonce(Date.now())}
          className="gap-2"
        >
          <RefreshCw className="size-4" />
          {dict.analytics.refresh}
        </Button>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex"
        >
          <Button variant="outline" size="sm" className="gap-2">
            <ExternalLink className="size-4" />
            {dict.analytics.openInGrafana}
          </Button>
        </a>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-border bg-background">
        <iframe
          key={iframeSrc}
          src={iframeSrc}
          title="Apache DevLake — Grafana"
          className="h-[80vh] w-full"
          // Grafana needs these to render its charts when embedded.
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
          loading="lazy"
        />
      </div>
    </div>
  );
}
