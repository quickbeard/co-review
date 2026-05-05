"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  CheckCircle2,
  Link2,
  Link2Off,
  List,
  MoreHorizontal,
  Pencil,
  Send,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import type { GitProvider } from "@/lib/api/types";
import {
  deleteWebhook,
  registerWebhook,
  testWebhook,
  unregisterWebhook,
  type WebhookRegistration,
} from "@/lib/api/webhooks";
import { WebhookStatusBadge } from "./webhook-status-badge";
import { WebhookDeliveriesDrawer } from "./webhook-deliveries-drawer";

interface WebhookListProps {
  webhooks: WebhookRegistration[];
  providers: GitProvider[];
  lang: string;
  // Nested (per-provider) callers hide the provider column and supply their
  // own URLs for the "Add" empty-state CTA and per-row "Edit" link. Left
  // undefined, the list falls back to the top-level /webhooks routes.
  //
  // Note: both must be plain strings (not functions) so this component can
  // be passed them from a server component. `editHrefBase` is the directory
  // that holds each webhook, i.e. the final URL becomes
  // `${editHrefBase}/${webhook.id}/edit`.
  hideProviderColumn?: boolean;
  addHref?: string;
  editHrefBase?: string;
}

type RowAction = "register" | "unregister" | "test" | "delete" | null;

export function WebhookList({
  webhooks,
  providers,
  lang,
  hideProviderColumn,
  addHref,
  editHrefBase,
}: WebhookListProps) {
  const dict = useDictionary();
  const router = useRouter();
  const addCtaHref = addHref ?? `/${lang}/webhooks/new`;
  const resolveEditHref = (w: WebhookRegistration) =>
    editHrefBase
      ? `${editHrefBase}/${w.id}/edit`
      : `/${lang}/webhooks/${w.id}/edit`;

  const [busyId, setBusyId] = useState<number | null>(null);
  const [busyAction, setBusyAction] = useState<RowAction>(null);
  const [deliveriesFor, setDeliveriesFor] =
    useState<WebhookRegistration | null>(null);

  // Resolve provider label/type once per provider id so every row stays O(1).
  const providerLookup = new Map(providers.map((p) => [p.id, p]));

  // Shared helper: run an async row action, surface errors, refresh on success.
  async function runRowAction(
    id: number,
    action: RowAction,
    exec: () => Promise<{ success: boolean; error?: string }>,
  ) {
    setBusyId(id);
    setBusyAction(action);
    try {
      const result = await exec();
      if (!result.success) {
        alert(result.error || dict.webhooks.errors.actionFailed);
        return;
      }
      router.refresh();
    } finally {
      setBusyId(null);
      setBusyAction(null);
    }
  }

  function handleRegister(id: number) {
    return runRowAction(id, "register", () => registerWebhook(id));
  }

  function handleUnregister(id: number) {
    return runRowAction(id, "unregister", () => unregisterWebhook(id));
  }

  async function handleTest(id: number) {
    setBusyId(id);
    setBusyAction("test");
    try {
      const result = await testWebhook(id);
      if (!result.success) {
        alert(result.error || dict.webhooks.errors.actionFailed);
        return;
      }
      alert(result.data?.message || dict.webhooks.messages.testSent);
    } finally {
      setBusyId(null);
      setBusyAction(null);
    }
  }

  function handleDelete(webhook: WebhookRegistration) {
    if (!confirm(dict.webhooks.deleteConfirm.replace("{repo}", webhook.repo))) {
      return;
    }
    return runRowAction(webhook.id, "delete", () => deleteWebhook(webhook.id));
  }

  if (webhooks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-8 text-center">
        <h3 className="text-lg font-medium text-foreground">
          {dict.webhooks.empty.title}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {dict.webhooks.empty.description}
        </p>
        <Link href={addCtaHref} className="mt-4">
          <Button>{dict.webhooks.addWebhook}</Button>
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{dict.webhooks.table.repo}</TableHead>
              {!hideProviderColumn && (
                <TableHead>{dict.webhooks.table.provider}</TableHead>
              )}
              <TableHead>{dict.webhooks.table.url}</TableHead>
              <TableHead>{dict.webhooks.table.events}</TableHead>
              <TableHead>{dict.webhooks.table.status}</TableHead>
              <TableHead className="w-[70px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {webhooks.map((w) => {
              const provider = providerLookup.get(w.git_provider_id);
              const isBusy = busyId === w.id;
              return (
                <TableRow key={w.id}>
                  <TableCell className="font-medium">
                    <div>{w.repo}</div>
                    {w.last_error && (
                      <div className="mt-1 text-xs text-destructive">
                        {w.last_error}
                      </div>
                    )}
                  </TableCell>
                  {!hideProviderColumn && (
                    <TableCell>
                      <div className="text-sm">
                        {provider?.name ?? `#${w.git_provider_id}`}
                      </div>
                      {provider && (
                        <div className="text-xs text-muted-foreground">
                          {provider.type}
                        </div>
                      )}
                    </TableCell>
                  )}
                  <TableCell className="max-w-[240px]">
                    <code className="block truncate font-mono text-xs text-muted-foreground">
                      {w.target_url}
                    </code>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {(w.events ?? []).slice(0, 3).map((ev) => (
                        <span
                          key={ev}
                          className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs"
                        >
                          {ev}
                        </span>
                      ))}
                      {(w.events?.length ?? 0) > 3 && (
                        <span className="text-xs text-muted-foreground">
                          +{(w.events?.length ?? 0) - 3}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <WebhookStatusBadge status={w.status} dict={dict} />
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted disabled:opacity-50"
                        disabled={isBusy}
                      >
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">
                          {dict.webhooks.table.actions}
                        </span>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        {w.status !== "registered" && (
                          <DropdownMenuItem
                            onClick={() => handleRegister(w.id)}
                          >
                            <Link2 className="mr-2 h-4 w-4" />
                            {busyAction === "register" && isBusy
                              ? dict.webhooks.actions.registering
                              : dict.webhooks.actions.register}
                          </DropdownMenuItem>
                        )}
                        {w.status === "registered" && (
                          <DropdownMenuItem
                            onClick={() => handleUnregister(w.id)}
                          >
                            <Link2Off className="mr-2 h-4 w-4" />
                            {dict.webhooks.actions.unregister}
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          onClick={() => handleTest(w.id)}
                          disabled={w.status !== "registered"}
                        >
                          <Send className="mr-2 h-4 w-4" />
                          {dict.webhooks.actions.test}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setDeliveriesFor(w)}
                          disabled={!w.external_id}
                        >
                          <List className="mr-2 h-4 w-4" />
                          {dict.webhooks.actions.deliveries}
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Link
                            href={resolveEditHref(w)}
                            className="flex w-full items-center"
                          >
                            <Pencil className="mr-2 h-4 w-4" />
                            {dict.webhooks.actions.edit}
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => handleDelete(w)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {dict.webhooks.actions.delete}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <WebhookDeliveriesDrawer
        webhook={deliveriesFor}
        open={!!deliveriesFor}
        onClose={() => setDeliveriesFor(null)}
      />

      {/* Tiny dot shown when a row is busy; keeps the Table component lean. */}
      {busyId !== null && (
        <div className="fixed bottom-4 right-4 flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground shadow-lg">
          <CheckCircle2 className="h-4 w-4 animate-pulse" />
          {dict.webhooks.messages.working}
        </div>
      )}
    </>
  );
}
