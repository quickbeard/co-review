export const dynamic = "force-dynamic";

// "Credentials" tab under /git-providers/{id}/. The page-level header, back
// link, and the tab strip are rendered by the shared layout above; this
// route owns just the edit form.

import { notFound } from "next/navigation";

import { GitProviderForm } from "@/components/git-providers";
import { hasLocale } from "@/lib/i18n/config";
import { getGitProvider } from "@/lib/api/git-providers";

export default async function EditGitProviderPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  if (!hasLocale(lang)) notFound();

  const result = await getGitProvider(id);
  if (!result.success || !result.data) {
    notFound();
  }

  return (
    <div className="max-w-xl rounded-lg border border-border bg-background p-6">
      <GitProviderForm provider={result.data} lang={lang} />
    </div>
  );
}
