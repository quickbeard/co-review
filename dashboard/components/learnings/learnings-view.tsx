"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Lightbulb,
  RefreshCw,
  Trash2,
  GitBranch,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  deleteLearning,
  getLearnings,
  type Learning,
  type LearningsResponse,
} from "@/lib/api/learnings";

interface LearningsViewProps {
  initial: LearningsResponse | null;
  initialError?: string | null;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString();
  } catch {
    return "—";
  }
}

function getSourceLabel(
  learning: Learning,
  prLabel: string,
  unknownLabel: string,
): string {
  const meta = learning.metadata ?? {};
  const pr = meta["pr_number"] ?? meta["prNumber"];
  if (typeof pr === "number" || typeof pr === "string") {
    return prLabel.replace("{pr}", String(pr));
  }
  return unknownLabel;
}

export function LearningsView({ initial, initialError }: LearningsViewProps) {
  const dict = useDictionary();

  const [data, setData] = useState<LearningsResponse | null>(initial);
  const [error, setError] = useState<string | null>(initialError ?? null);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [repoFilter, setRepoFilter] = useState<string>("");
  const [limit, setLimit] = useState<number>(100);

  const fetchLearnings = useCallback(async () => {
    setLoading(true);
    const result = await getLearnings({
      repo: repoFilter || undefined,
      limit,
    });
    if (result.success && result.data) {
      setData(result.data);
      setError(null);
    } else {
      setError(result.error ?? dict.learnings.apiError);
    }
    setLoading(false);
  }, [repoFilter, limit, dict.learnings.apiError]);

  useEffect(() => {
    // Re-fetch whenever filters change, but skip the very first render when
    // we already have server-rendered `initial` data for the default filters.
    if (initial && repoFilter === "" && limit === 100) return;
    void fetchLearnings();
  }, [repoFilter, limit, fetchLearnings, initial]);

  async function handleDelete(id: string | null) {
    if (!id) return;
    if (!confirm(dict.learnings.deleteDialog.description)) return;
    setDeletingId(id);
    const result = await deleteLearning(id);
    setDeletingId(null);
    if (result.success) {
      await fetchLearnings();
    } else {
      alert(result.error ?? "Failed to delete learning");
    }
  }

  const items = data?.items ?? [];
  const repos = data?.repos ?? [];
  const enabled = data?.enabled ?? true;

  const stats = useMemo(
    () => ({
      total: data?.total ?? 0,
      repos: repos.length,
    }),
    [data?.total, repos.length],
  );

  if (!enabled) {
    return (
      <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-6 text-yellow-800 dark:text-yellow-300">
        <h3 className="text-base font-semibold">
          {dict.learnings.disabled.title}
        </h3>
        <p className="mt-1 text-sm">{dict.learnings.disabled.description}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {dict.learnings.apiError}: {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-background p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">
              {dict.learnings.stats.total}
            </p>
            <Lightbulb className="size-4 text-primary" />
          </div>
          <p className="mt-2 text-2xl font-semibold">{stats.total}</p>
        </div>
        <div className="rounded-lg border border-border bg-background p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">
              {dict.learnings.stats.repos}
            </p>
            <GitBranch className="size-4 text-primary" />
          </div>
          <p className="mt-2 text-2xl font-semibold">{stats.repos}</p>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-border bg-background p-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex flex-col gap-1">
            <label
              htmlFor="learnings-repo-filter"
              className="text-xs font-medium text-muted-foreground"
            >
              {dict.learnings.filters.repo}
            </label>
            <select
              id="learnings-repo-filter"
              value={repoFilter}
              onChange={(e) => setRepoFilter(e.target.value)}
              className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
            >
              <option value="">{dict.learnings.filters.allRepos}</option>
              {repos.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label
              htmlFor="learnings-limit"
              className="text-xs font-medium text-muted-foreground"
            >
              {dict.learnings.filters.limit}
            </label>
            <select
              id="learnings-limit"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={250}>250</option>
              <option value={500}>500</option>
            </select>
          </div>
        </div>
        <Button
          variant="outline"
          onClick={() => void fetchLearnings()}
          disabled={loading}
          className="gap-2"
        >
          {loading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <RefreshCw className="size-4" />
          )}
          {dict.learnings.filters.refresh}
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-10 text-center">
          <Lightbulb className="size-10 text-muted-foreground" />
          <h3 className="mt-3 text-lg font-medium text-foreground">
            {dict.learnings.empty.title}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {dict.learnings.empty.description}
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[20%]">
                  {dict.learnings.table.repo}
                </TableHead>
                <TableHead>{dict.learnings.table.learning}</TableHead>
                <TableHead className="w-[120px]">
                  {dict.learnings.table.source}
                </TableHead>
                <TableHead className="w-[180px]">
                  {dict.learnings.table.createdAt}
                </TableHead>
                <TableHead className="w-[80px] text-right">
                  {dict.learnings.table.actions}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item, idx) => (
                <TableRow key={item.id ?? `${item.repo}-${idx}`}>
                  <TableCell className="align-top font-medium">
                    {item.repo ? (
                      <Badge variant="secondary" className="font-normal">
                        {item.repo}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="whitespace-pre-wrap align-top text-sm">
                    {item.text}
                  </TableCell>
                  <TableCell className="align-top text-xs text-muted-foreground">
                    {getSourceLabel(
                      item,
                      dict.learnings.source.pr,
                      dict.learnings.source.unknown,
                    )}
                  </TableCell>
                  <TableCell className="align-top text-xs text-muted-foreground">
                    {formatDate(item.createdAt)}
                  </TableCell>
                  <TableCell className="align-top text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => void handleDelete(item.id)}
                      disabled={!item.id || deletingId === item.id}
                      aria-label={dict.learnings.actions.delete}
                    >
                      {deletingId === item.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Trash2 className="size-4" />
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
