"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import type { Dictionary } from "@/app/dictionaries";
import {
  getWebhookDeliveries,
  type WebhookDelivery,
  type WebhookRegistration,
} from "@/lib/api/webhooks";

interface WebhookDeliveriesDrawerProps {
  webhook: WebhookRegistration | null;
  open: boolean;
  onClose: () => void;
}

/** Fetches and lists deliveries. Mounted only when the drawer is open with a row selected (`key={webhook.id}` resets state when switching rows). */
function WebhookDeliveriesPanel({
  webhook,
  dict,
}: {
  webhook: WebhookRegistration;
  dict: Dictionary;
}) {
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getWebhookDeliveries(webhook.id, 30).then((r) => {
      if (cancelled) return;
      if (r.success) {
        setDeliveries(r.data ?? []);
      } else {
        setError(r.error ?? dict.webhooks.errors.fetchDeliveriesFailed);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [webhook.id, dict]);

  return (
    <>
      {loading && (
        <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {dict.webhooks.deliveries.loading}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {!loading && !error && deliveries.length === 0 && (
        <div className="py-8 text-center text-sm text-muted-foreground">
          {dict.webhooks.deliveries.empty}
        </div>
      )}

      {!loading && !error && deliveries.length > 0 && (
        <div className="max-h-[480px] overflow-y-auto">
          <ul className="divide-y divide-border">
            {deliveries.map((d) => {
              const ok =
                d.status_code !== null &&
                d.status_code >= 200 &&
                d.status_code < 300;
              return (
                <li key={d.id} className="py-2.5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={ok ? "default" : "destructive"}>
                          {d.status_code ?? "?"}
                        </Badge>
                        <span className="font-mono text-xs">
                          {d.event ?? "-"}
                          {d.action ? `.${d.action}` : ""}
                        </span>
                        {d.redelivery && (
                          <Badge variant="outline">redelivery</Badge>
                        )}
                      </div>
                      {d.status && (
                        <div className="mt-1 text-xs text-muted-foreground">
                          {d.status}
                        </div>
                      )}
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      {d.delivered_at
                        ? new Date(d.delivered_at).toLocaleString()
                        : "-"}
                      {d.duration_ms !== null && (
                        <div>{Math.round(d.duration_ms)} ms</div>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </>
  );
}

export function WebhookDeliveriesDrawer({
  webhook,
  open,
  onClose,
}: WebhookDeliveriesDrawerProps) {
  const dict = useDictionary();

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{dict.webhooks.deliveries.title}</DialogTitle>
          <DialogDescription>{webhook ? webhook.repo : ""}</DialogDescription>
        </DialogHeader>

        {open && webhook ? (
          <WebhookDeliveriesPanel
            key={webhook.id}
            webhook={webhook}
            dict={dict}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
