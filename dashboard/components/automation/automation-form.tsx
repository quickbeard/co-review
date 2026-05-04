"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  reloadAutomationConfig,
  updateAutomationConfig,
  type AutomationConfig,
  type AutomationProviderKey,
  type ProviderAutomationConfig,
} from "@/lib/api/automation";
import { cn } from "@/lib/utils";
import { StringListEditor } from "./string-list-editor";

interface AutomationFormProps {
  initial: AutomationConfig;
}

interface ProviderTab {
  key: AutomationProviderKey;
  labelKey:
    | "github"
    | "gitlab"
    | "bitbucket"
    | "azure"
    | "gitea";
  showPushTrigger: boolean;
  showPrActions: boolean;
  showDraft: boolean;
}

const TABS: ProviderTab[] = [
  {
    key: "github_app",
    labelKey: "github",
    showPushTrigger: true,
    showPrActions: true,
    showDraft: true,
  },
  {
    key: "gitlab",
    labelKey: "gitlab",
    showPushTrigger: true,
    showPrActions: false,
    showDraft: false,
  },
  {
    key: "bitbucket_app",
    labelKey: "bitbucket",
    showPushTrigger: true,
    showPrActions: false,
    showDraft: false,
  },
  {
    key: "azure_devops",
    labelKey: "azure",
    showPushTrigger: false,
    showPrActions: false,
    showDraft: false,
  },
  {
    key: "gitea",
    labelKey: "gitea",
    showPushTrigger: true,
    showPrActions: false,
    showDraft: false,
  },
];

const COMMAND_PRESETS = [
  "/describe",
  "/review",
  "/improve",
  "/agentic_review",
  "/ask",
  "/update_changelog",
];

const PR_ACTION_OPTIONS = [
  "opened",
  "reopened",
  "ready_for_review",
  "review_requested",
] as const;

function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function AutomationForm({ initial }: AutomationFormProps) {
  const dict = useDictionary();
  const [config, setConfig] = useState<AutomationConfig>(initial);
  const [activeTab, setActiveTab] = useState<AutomationProviderKey>("github_app");
  const [saving, setSaving] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const hasChanges = useMemo(
    () => !deepEqual(config, initial),
    [config, initial],
  );

  useEffect(() => {
    if (success || error) {
      const t = setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 5000);
      return () => clearTimeout(t);
    }
  }, [success, error]);

  function updateProvider(
    key: AutomationProviderKey,
    patch: Partial<ProviderAutomationConfig>,
  ) {
    setConfig((prev) => ({
      ...prev,
      [key]: { ...prev[key], ...patch },
    }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    const result = await updateAutomationConfig(config);
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error ?? dict.automation.errors.saveFailed);
      return;
    }
    setConfig(result.data);
    setSuccess(dict.automation.messages.saved);
  }

  async function handleReload() {
    setReloading(true);
    setError(null);
    setSuccess(null);
    const result = await reloadAutomationConfig();
    setReloading(false);
    if (!result.success) {
      setError(result.error ?? dict.automation.errors.reloadFailed);
      return;
    }
    setSuccess(dict.automation.messages.reloaded);
  }

  const activeTabDef = TABS.find((t) => t.key === activeTab)!;
  const activeProvider = config[activeTab];

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

      <Card>
        <CardHeader>
          <CardTitle>{dict.automation.global.title}</CardTitle>
          <CardDescription>{dict.automation.global.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              checked={config.disable_auto_feedback}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  disable_auto_feedback: e.target.checked,
                }))
              }
            />
            <div className="space-y-0.5">
              <div className="text-sm font-medium text-foreground">
                {dict.automation.global.disableAutoFeedback}
              </div>
              <p className="text-xs text-muted-foreground">
                {dict.automation.global.disableAutoFeedbackHelp}
              </p>
            </div>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{dict.automation.provider.title}</CardTitle>
          <CardDescription>
            {dict.automation.provider.description}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div
            role="tablist"
            className="flex flex-wrap gap-1 rounded-md border border-border bg-muted p-1"
          >
            {TABS.map((tab) => {
              const isActive = tab.key === activeTab;
              return (
                <button
                  key={tab.key}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "flex-1 min-w-[80px] rounded-sm px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {dict.automation.providers[tab.labelKey]}
                </button>
              );
            })}
          </div>

          <div className="space-y-6">
            <StringListEditor
              id={`${activeTab}-pr-commands`}
              label={dict.automation.fields.prCommands}
              description={dict.automation.fields.prCommandsHelp}
              values={activeProvider.pr_commands ?? []}
              onChange={(next) =>
                updateProvider(activeTab, { pr_commands: next })
              }
              placeholder="/review --pr_reviewer.extra_instructions='…'"
              presets={COMMAND_PRESETS}
              disabled={saving}
              emptyLabel={dict.automation.fields.prCommandsEmpty}
              addLabel={dict.automation.fields.add}
            />

            <StringListEditor
              id={`${activeTab}-push-commands`}
              label={dict.automation.fields.pushCommands}
              description={dict.automation.fields.pushCommandsHelp}
              values={activeProvider.push_commands ?? []}
              onChange={(next) =>
                updateProvider(activeTab, { push_commands: next })
              }
              placeholder="/review"
              presets={COMMAND_PRESETS}
              disabled={saving}
              emptyLabel={dict.automation.fields.pushCommandsEmpty}
              addLabel={dict.automation.fields.add}
            />

            {activeTabDef.showPushTrigger && (
              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 accent-primary"
                  checked={!!activeProvider.handle_push_trigger}
                  onChange={(e) =>
                    updateProvider(activeTab, {
                      handle_push_trigger: e.target.checked,
                    })
                  }
                />
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">
                    {dict.automation.fields.handlePushTrigger}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {dict.automation.fields.handlePushTriggerHelp}
                  </p>
                </div>
              </label>
            )}

            {activeTabDef.showPrActions && (
              <div className="space-y-2">
                <Label className="text-sm font-medium">
                  {dict.automation.fields.handlePrActions}
                </Label>
                <p className="text-xs text-muted-foreground">
                  {dict.automation.fields.handlePrActionsHelp}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {PR_ACTION_OPTIONS.map((action) => {
                    const selected =
                      activeProvider.handle_pr_actions?.includes(action) ??
                      false;
                    return (
                      <button
                        key={action}
                        type="button"
                        onClick={() => {
                          const current =
                            activeProvider.handle_pr_actions ?? [];
                          const next = selected
                            ? current.filter((a) => a !== action)
                            : [...current, action];
                          updateProvider(activeTab, {
                            handle_pr_actions: next,
                          });
                        }}
                        className={cn(
                          "rounded-full border px-3 py-1 font-mono text-xs transition-colors",
                          selected
                            ? "border-primary/60 bg-primary/15 text-primary"
                            : "border-border bg-background text-muted-foreground hover:text-foreground",
                        )}
                      >
                        {action}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {activeTabDef.showDraft && (
              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3">
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 accent-primary"
                  checked={!!activeProvider.feedback_on_draft_pr}
                  onChange={(e) =>
                    updateProvider(activeTab, {
                      feedback_on_draft_pr: e.target.checked,
                    })
                  }
                />
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">
                    {dict.automation.fields.feedbackOnDraft}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {dict.automation.fields.feedbackOnDraftHelp}
                  </p>
                </div>
              </label>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleSave} disabled={!hasChanges || saving}>
          {saving ? (
            <>
              <Loader2 className="mr-2 size-4 animate-spin" />
              {dict.automation.actions.saving}
            </>
          ) : (
            <>
              <Save className="mr-2 size-4" />
              {dict.automation.actions.save}
            </>
          )}
        </Button>
        <Button
          variant="outline"
          onClick={handleReload}
          disabled={reloading || saving}
          title={dict.automation.actions.reloadHelp}
        >
          {reloading ? (
            <Loader2 className="mr-2 size-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 size-4" />
          )}
          {dict.automation.actions.reload}
        </Button>
      </div>
    </div>
  );
}
