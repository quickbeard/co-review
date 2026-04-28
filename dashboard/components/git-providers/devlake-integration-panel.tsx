"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  enqueueDevLakeSync,
  getDevLakeIntegration,
  getDevLakeSyncJobStatus,
  updateDevLakeIntegration,
  validateDevLakeIntegration,
} from "@/lib/api/git-providers";
import { useDictionary } from "@/lib/i18n/dictionary-context";

interface DevLakeIntegrationPanelProps {
  providerId: number;
}

export function DevLakeIntegrationPanel({
  providerId,
}: DevLakeIntegrationPanelProps) {
  const dict = useDictionary();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [scopesText, setScopesText] = useState("[]");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validateMessage, setValidateMessage] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const result = await getDevLakeIntegration(providerId);
      if (!mounted) return;
      if (!result.success || !result.data) {
        setError(result.error || "Failed to load DevLake settings");
        setLoading(false);
        return;
      }
      setEnabled(result.data.enabled);
      setProjectName(result.data.projectName || "");
      setScopesText(JSON.stringify(result.data.selectedScopes || [], null, 2));
      setStatus(result.data.lastSyncStatus);
      setLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, [providerId]);

  const parsedScopes = useMemo(() => {
    try {
      const parsed = JSON.parse(scopesText);
      if (!Array.isArray(parsed)) return null;
      return parsed;
    } catch {
      return null;
    }
  }, [scopesText]);

  async function handleSave() {
    setError(null);
    setValidateMessage(null);
    if (!parsedScopes) {
      setError(dict.gitProviders.devlake.invalidScopesJson);
      return;
    }
    setSaving(true);
    const result = await updateDevLakeIntegration(providerId, {
      enabled,
      projectName: projectName || undefined,
      selectedScopes: parsedScopes,
    });
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error || "Failed to save DevLake settings");
      return;
    }
    setStatus(result.data.lastSyncStatus);
  }

  async function handleValidate() {
    setError(null);
    setValidateMessage(null);
    const result = await validateDevLakeIntegration(providerId);
    if (!result.success || !result.data) {
      setError(result.error || "Validation failed");
      return;
    }
    setValidateMessage(result.data.message);
  }

  async function handleSync() {
    setError(null);
    setValidateMessage(null);
    setSyncing(true);
    const accepted = await enqueueDevLakeSync(providerId);
    if (!accepted.success || !accepted.data) {
      setSyncing(false);
      setError(accepted.error || "Failed to queue sync");
      return;
    }
    const jobId = accepted.data.job_id;
    setStatus("queued");

    for (let i = 0; i < 45; i++) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const job = await getDevLakeSyncJobStatus(providerId, jobId);
      if (!job.success || !job.data) {
        continue;
      }
      setStatus(job.data.status);
      if (job.data.status === "succeeded") {
        setSyncing(false);
        return;
      }
      if (job.data.status === "failed") {
        setSyncing(false);
        setError(job.data.error || dict.gitProviders.devlake.syncFailed);
        return;
      }
    }

    setSyncing(false);
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-background p-6 text-sm text-muted-foreground">
        {dict.gitProviders.devlake.loading}
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-lg border border-border bg-background p-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">
          {dict.gitProviders.devlake.title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {dict.gitProviders.devlake.description}
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4 rounded border-border text-primary"
        />
        {dict.gitProviders.devlake.enabled}
      </label>

      <div className="space-y-2">
        <Label htmlFor="devlake-project-name">
          {dict.gitProviders.devlake.projectName}
        </Label>
        <p className="text-xs text-muted-foreground">
          {dict.gitProviders.devlake.projectNameHelpReuse}
        </p>
        <p className="text-xs text-muted-foreground">
          {dict.gitProviders.devlake.projectNameHelpCreate}
        </p>
        <Input
          id="devlake-project-name"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder={dict.gitProviders.devlake.projectNamePlaceholder}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="devlake-scopes">{dict.gitProviders.devlake.scopes}</Label>
        <textarea
          id="devlake-scopes"
          value={scopesText}
          onChange={(e) => setScopesText(e.target.value)}
          className="min-h-36 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-foreground"
          placeholder='[{"scopeId":"123","name":"org/repo","fullName":"org/repo"}]'
        />
      </div>

      {status && (
        <p className="text-sm text-muted-foreground">
          {dict.gitProviders.devlake.lastStatus}: {status}
        </p>
      )}
      {validateMessage && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400">
          {validateMessage}
        </p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={handleSave} disabled={saving || syncing}>
          {saving ? dict.gitProviders.devlake.saving : dict.gitProviders.devlake.save}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={handleValidate}
          disabled={saving || syncing}
        >
          {dict.gitProviders.devlake.validate}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={handleSync}
          disabled={saving || syncing}
        >
          {syncing ? dict.gitProviders.devlake.syncing : dict.gitProviders.devlake.sync}
        </Button>
      </div>
    </div>
  );
}
