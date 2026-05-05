"use client";

import { useEffect, useMemo, useState } from "react";
import { Info, Loader2, RefreshCw, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StringListEditor } from "@/components/automation/string-list-editor";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  KNOWLEDGE_BASE_TEMPLATE_RULES,
  reloadKnowledgeBaseConfig,
  updateKnowledgeBaseConfig,
  type KnowledgeBaseConfig,
} from "@/lib/api/knowledge-base";

interface KnowledgeBaseFormProps {
  initial: KnowledgeBaseConfig;
}

function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/** Clamp + coerce a numeric input value; returns ``fallback`` if empty. */
function parseNumber(
  raw: string,
  fallback: number,
  opts: { min?: number; max?: number; integer?: boolean } = {},
): number {
  if (raw.trim() === "") return fallback;
  const n = opts.integer ? parseInt(raw, 10) : Number(raw);
  if (Number.isNaN(n)) return fallback;
  let v = n;
  if (opts.min !== undefined) v = Math.max(opts.min, v);
  if (opts.max !== undefined) v = Math.min(opts.max, v);
  return v;
}

export function KnowledgeBaseForm({ initial }: KnowledgeBaseFormProps) {
  const dict = useDictionary();
  const t = dict.knowledgeBase;

  const [config, setConfig] = useState<KnowledgeBaseConfig>(initial);
  const [saving, setSaving] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Track whether the last user action explicitly opted into preset rules.
  // We only seed once per transition (explicit-on -> explicit-off with empty
  // rules) so repeated saves with an intentionally-empty list stay empty.
  const [seeded, setSeeded] = useState(false);

  const hasChanges = useMemo(
    () => !deepEqual(config, initial),
    [config, initial],
  );

  useEffect(() => {
    if (success || error) {
      const tid = setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 5000);
      return () => clearTimeout(tid);
    }
  }, [success, error]);

  function setField<K extends keyof KnowledgeBaseConfig>(
    key: K,
    value: KnowledgeBaseConfig[K],
  ) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  function toggleExplicitLearn(next: boolean) {
    setConfig((prev) => {
      // When turning OFF explicit learn with no rules configured yet, seed the
      // template rules so the user immediately sees concrete examples and the
      // system never silently stops capturing anything. Mirrors the
      // server-side safety net in _merge_knowledge_base_update (api.py).
      if (!next && prev.extraction_rules.length === 0 && !seeded) {
        setSeeded(true);
        return {
          ...prev,
          explicit_learn_enabled: false,
          extraction_rules: [...KNOWLEDGE_BASE_TEMPLATE_RULES],
        };
      }
      // Turning explicit learn back on: leave rules intact (user may want them
      // back if they toggle off again later, and rules don't hurt when
      // explicit is on since they're ignored).
      return { ...prev, explicit_learn_enabled: next };
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    const result = await updateKnowledgeBaseConfig(config);
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error ?? t.errors.saveFailed);
      return;
    }
    setConfig(result.data);
    setSeeded(false);
    setSuccess(t.messages.saved);
  }

  async function handleReload() {
    setReloading(true);
    setError(null);
    setSuccess(null);
    const result = await reloadKnowledgeBaseConfig();
    setReloading(false);
    if (!result.success) {
      setError(result.error ?? t.errors.reloadFailed);
      return;
    }
    setSuccess(t.messages.reloaded);
  }

  const rulesDisabled = config.explicit_learn_enabled;

  return (
    <div className="space-y-6">
      {success && (
        <div className="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400">
          {success}
        </div>
      )}
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Master switch */}
      <Card>
        <CardHeader>
          <CardTitle>{t.master.title}</CardTitle>
          <CardDescription>{t.master.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              checked={config.enabled}
              onChange={(e) => setField("enabled", e.target.checked)}
            />
            <div className="space-y-0.5">
              <div className="text-sm font-medium text-foreground">
                {t.master.enabledLabel}
              </div>
              <p className="text-xs text-muted-foreground">
                {t.master.enabledHelp}
              </p>
            </div>
          </label>
        </CardContent>
      </Card>

      {/* Capture: explicit /learn + extraction rules */}
      <Card>
        <CardHeader>
          <CardTitle>{t.capture.title}</CardTitle>
          <CardDescription>{t.capture.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              checked={config.explicit_learn_enabled}
              onChange={(e) => toggleExplicitLearn(e.target.checked)}
              disabled={!config.enabled}
            />
            <div className="space-y-0.5">
              <div className="text-sm font-medium text-foreground">
                {t.capture.explicitLearnLabel}
              </div>
              <p className="text-xs text-muted-foreground">
                {t.capture.explicitLearnHelp}
              </p>
            </div>
          </label>

          <div className="space-y-2">
            <Label htmlFor="kb-learn-command">{t.capture.commandLabel}</Label>
            <Input
              id="kb-learn-command"
              value={config.learn_command}
              onChange={(e) => setField("learn_command", e.target.value)}
              disabled={!config.enabled || !config.explicit_learn_enabled}
              className="max-w-xs"
              placeholder="/learn"
            />
            <p className="text-xs text-muted-foreground">
              {t.capture.commandHelp}
            </p>
          </div>

          <div
            className={cn(
              "rounded-md border p-4",
              rulesDisabled
                ? "border-border/60 bg-muted/30"
                : "border-primary/40 bg-primary/5",
            )}
          >
            <div className="mb-3 flex items-start gap-2">
              <Info className="mt-0.5 size-4 shrink-0 text-primary" />
              <div>
                <div className="text-sm font-medium text-foreground">
                  {t.rules.title}
                </div>
                <p className="text-xs text-muted-foreground">
                  {rulesDisabled ? t.rules.disabledHelp : t.rules.activeHelp}
                </p>
              </div>
            </div>

            <StringListEditor
              id="kb-extraction-rules"
              label={t.rules.label}
              description={t.rules.description}
              values={config.extraction_rules}
              onChange={(next) => setField("extraction_rules", next)}
              placeholder={t.rules.placeholder}
              presets={KNOWLEDGE_BASE_TEMPLATE_RULES as unknown as string[]}
              disabled={!config.enabled || rulesDisabled}
              emptyLabel={t.rules.emptyLabel}
              addLabel={t.rules.addLabel}
            />
          </div>
        </CardContent>
      </Card>

      {/* Retrieval tuning */}
      <Card>
        <CardHeader>
          <CardTitle>{t.retrieval.title}</CardTitle>
          <CardDescription>{t.retrieval.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              checked={config.apply_to_review}
              onChange={(e) => setField("apply_to_review", e.target.checked)}
              disabled={!config.enabled}
            />
            <div className="space-y-0.5">
              <div className="text-sm font-medium text-foreground">
                {t.retrieval.applyToReviewLabel}
              </div>
              <p className="text-xs text-muted-foreground">
                {t.retrieval.applyToReviewHelp}
              </p>
            </div>
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="kb-max-retrieved">
                {t.retrieval.maxRetrievedLabel}
              </Label>
              <Input
                id="kb-max-retrieved"
                type="number"
                min={0}
                max={50}
                step={1}
                value={config.max_retrieved_learnings}
                onChange={(e) =>
                  setField(
                    "max_retrieved_learnings",
                    parseNumber(e.target.value, initial.max_retrieved_learnings, {
                      min: 0,
                      max: 50,
                      integer: true,
                    }),
                  )
                }
                disabled={!config.enabled}
              />
              <p className="text-xs text-muted-foreground">
                {t.retrieval.maxRetrievedHelp}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="kb-max-summary">
                {t.retrieval.maxSummaryLabel}
              </Label>
              <Input
                id="kb-max-summary"
                type="number"
                min={100}
                max={10000}
                step={100}
                value={config.max_summary_chars}
                onChange={(e) =>
                  setField(
                    "max_summary_chars",
                    parseNumber(e.target.value, initial.max_summary_chars, {
                      min: 100,
                      max: 10000,
                      integer: true,
                    }),
                  )
                }
                disabled={!config.enabled}
              />
              <p className="text-xs text-muted-foreground">
                {t.retrieval.maxSummaryHelp}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Refinement / advanced */}
      <Card>
        <CardHeader>
          <CardTitle>{t.refinement.title}</CardTitle>
          <CardDescription>{t.refinement.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="kb-duplicate-threshold">
              {t.refinement.duplicateThresholdLabel}
            </Label>
            <Input
              id="kb-duplicate-threshold"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={config.duplicate_threshold}
              onChange={(e) =>
                setField(
                  "duplicate_threshold",
                  parseNumber(e.target.value, initial.duplicate_threshold, {
                    min: 0,
                    max: 1,
                  }),
                )
              }
              disabled={!config.enabled}
              className="max-w-xs"
            />
            <p className="text-xs text-muted-foreground">
              {t.refinement.duplicateThresholdHelp}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Legacy section - deprecated but still toggleable */}
      <Card className="border-amber-500/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {t.legacy.title}
            <span className="rounded bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
              {t.legacy.deprecatedBadge}
            </span>
          </CardTitle>
          <CardDescription>{t.legacy.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              checked={config.capture_from_pr_comments}
              onChange={(e) =>
                setField("capture_from_pr_comments", e.target.checked)
              }
              disabled={!config.enabled}
            />
            <div className="space-y-0.5">
              <div className="text-sm font-medium text-foreground">
                {t.legacy.captureLabel}
              </div>
              <p className="text-xs text-muted-foreground">
                {t.legacy.captureHelp}
              </p>
            </div>
          </label>

          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              checked={config.require_agent_mention}
              onChange={(e) =>
                setField("require_agent_mention", e.target.checked)
              }
              disabled={!config.enabled || !config.capture_from_pr_comments}
            />
            <div className="space-y-0.5">
              <div className="text-sm font-medium text-foreground">
                {t.legacy.requireMentionLabel}
              </div>
              <p className="text-xs text-muted-foreground">
                {t.legacy.requireMentionHelp}
              </p>
            </div>
          </label>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={handleReload}
          disabled={reloading || saving}
        >
          {reloading ? (
            <Loader2 className="mr-2 size-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 size-4" />
          )}
          {t.actions.reload}
        </Button>

        <Button
          type="button"
          onClick={handleSave}
          disabled={saving || reloading || !hasChanges}
        >
          {saving ? (
            <Loader2 className="mr-2 size-4 animate-spin" />
          ) : (
            <Save className="mr-2 size-4" />
          )}
          {t.actions.save}
        </Button>
      </div>
    </div>
  );
}
