"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  updateTokenLimits,
  resetTokenLimits,
  type TokenLimits,
} from "@/lib/api/token-limits";

interface TokenLimitsFormProps {
  initialLimits: TokenLimits;
}

export function TokenLimitsForm({ initialLimits }: TokenLimitsFormProps) {
  const dict = useDictionary();
  const [pending, setPending] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [limits, setLimits] = useState<TokenLimits>(initialLimits);

  // Track if form has changes - computed value, not state
  const hasChanges = useMemo(() => {
    return (
      limits.max_description_tokens !== initialLimits.max_description_tokens ||
      limits.max_commits_tokens !== initialLimits.max_commits_tokens ||
      limits.max_model_tokens !== initialLimits.max_model_tokens ||
      limits.custom_model_max_tokens !== initialLimits.custom_model_max_tokens
    );
  }, [limits, initialLimits]);

  // Clear success/error messages after timeout
  useEffect(() => {
    if (success || error) {
      const timer = setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [success, error]);

  const handleInputChange = useCallback(
    (field: keyof TokenLimits) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value >= 0) {
        setLimits((prev) => ({ ...prev, [field]: value }));
      }
    },
    [],
  );

  async function handleSave() {
    setError(null);
    setSuccess(null);
    setPending(true);

    const result = await updateTokenLimits(limits);

    setPending(false);

    if (!result.success) {
      setError(result.error || dict.tokenLimits.form.errorGeneric);
      return;
    }

    if (result.data) {
      setLimits(result.data);
    }
    setSuccess(dict.tokenLimits.form.saveSuccess);
  }

  async function handleReset() {
    setError(null);
    setSuccess(null);
    setResetting(true);

    const result = await resetTokenLimits();

    setResetting(false);

    if (!result.success) {
      setError(result.error || dict.tokenLimits.form.errorGeneric);
      return;
    }

    if (result.data) {
      setLimits(result.data);
    }
    setSuccess(dict.tokenLimits.form.resetSuccess);
  }

  const fields: {
    key: keyof TokenLimits;
    labelKey: keyof typeof dict.tokenLimits.form;
    descKey: keyof typeof dict.tokenLimits.form;
  }[] = [
    {
      key: "max_description_tokens",
      labelKey: "maxDescriptionTokens",
      descKey: "maxDescriptionTokensHelp",
    },
    {
      key: "max_commits_tokens",
      labelKey: "maxCommitsTokens",
      descKey: "maxCommitsTokensHelp",
    },
    {
      key: "max_model_tokens",
      labelKey: "maxModelTokens",
      descKey: "maxModelTokensHelp",
    },
    {
      key: "custom_model_max_tokens",
      labelKey: "customModelMaxTokens",
      descKey: "customModelMaxTokensHelp",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{dict.tokenLimits.title}</CardTitle>
        <CardDescription>{dict.tokenLimits.description}</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
          {/* Success message */}
          {success && (
            <div className="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400">
              {success}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* Token limit fields */}
          <div className="grid gap-6 sm:grid-cols-2">
            {fields.map(({ key, labelKey, descKey }) => (
              <div key={key} className="space-y-2">
                <Label htmlFor={key}>
                  {dict.tokenLimits.form[labelKey] as string}
                </Label>
                <Input
                  id={key}
                  type="number"
                  min={0}
                  value={limits[key]}
                  onChange={handleInputChange(key)}
                  disabled={pending || resetting}
                />
                <p className="text-sm text-muted-foreground">
                  {dict.tokenLimits.form[descKey] as string}
                </p>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={handleSave} disabled={pending || !hasChanges}>
              {pending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {dict.tokenLimits.form.saving}
                </>
              ) : (
                dict.tokenLimits.form.save
              )}
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={resetting || pending}
            >
              {resetting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {dict.tokenLimits.form.resetting}
                </>
              ) : (
                <>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  {dict.tokenLimits.form.resetToDefaults}
                </>
              )}
            </Button>
          </div>
        </CardContent>
    </Card>
  );
}
