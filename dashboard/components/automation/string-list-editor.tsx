"use client";

import { useState, type KeyboardEvent } from "react";
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface StringListEditorProps {
  id: string;
  label: string;
  description?: string;
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  presets?: string[];
  disabled?: boolean;
  emptyLabel?: string;
  addLabel?: string;
}

export function StringListEditor({
  id,
  label,
  description,
  values,
  onChange,
  placeholder,
  presets,
  disabled,
  emptyLabel,
  addLabel,
}: StringListEditorProps) {
  const [draft, setDraft] = useState("");

  function commitDraft() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    if (values.includes(trimmed)) {
      setDraft("");
      return;
    }
    onChange([...values, trimmed]);
    setDraft("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      commitDraft();
    }
  }

  function removeAt(index: number) {
    const next = values.slice();
    next.splice(index, 1);
    onChange(next);
  }

  function addPreset(preset: string) {
    if (values.includes(preset)) return;
    onChange([...values, preset]);
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-sm font-medium">
        {label}
      </Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}

      <ul className="space-y-1.5">
        {values.length === 0 && emptyLabel && (
          <li className="rounded-md border border-dashed border-border bg-muted/40 p-2 text-xs text-muted-foreground">
            {emptyLabel}
          </li>
        )}
        {values.map((value, idx) => (
          <li
            key={`${value}-${idx}`}
            className="flex items-center gap-2 rounded-md border border-border bg-background p-1.5 pl-2"
          >
            <code className="flex-1 truncate font-mono text-xs text-foreground">
              {value}
            </code>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => removeAt(idx)}
              disabled={disabled}
              aria-label={`Remove ${value}`}
            >
              <X className="size-3.5" />
            </Button>
          </li>
        ))}
      </ul>

      <div className="flex gap-2">
        <Input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="font-mono text-xs"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={commitDraft}
          disabled={disabled || !draft.trim()}
          className="shrink-0"
        >
          <Plus className="mr-1 size-3.5" />
          {addLabel ?? "Add"}
        </Button>
      </div>

      {presets && presets.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {presets.map((preset) => {
            const active = values.includes(preset);
            return (
              <button
                key={preset}
                type="button"
                onClick={() => addPreset(preset)}
                disabled={disabled || active}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 font-mono text-xs transition-colors",
                  active
                    ? "border-border bg-muted text-muted-foreground"
                    : "border-primary/40 bg-primary/10 text-primary hover:bg-primary/20",
                  disabled && "cursor-not-allowed opacity-50",
                )}
              >
                {preset}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
