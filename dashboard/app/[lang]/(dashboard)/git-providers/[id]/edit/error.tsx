"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { useDictionary } from "@/lib/i18n/dictionary-context";

export default function EditGitProviderError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const dict = useDictionary();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center space-y-4 py-12">
      <div className="rounded-full bg-destructive/10 p-3">
        <AlertCircle className="size-6 text-destructive" />
      </div>
      <div className="text-center">
        <h2 className="text-lg font-semibold text-foreground">
          {dict.gitProviders.error.title}
        </h2>
        <p className="mt-1 text-muted-foreground">
          {dict.gitProviders.error.description}
        </p>
      </div>
      <Button onClick={reset}>{dict.gitProviders.error.retry}</Button>
    </div>
  );
}
