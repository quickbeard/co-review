export const dynamic = "force-dynamic";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { WebhookForm } from "@/components/webhooks";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { getGitProviders } from "@/lib/api/git-providers";

export default async function NewWebhookPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();

  const dict = await getDictionary(lang);
  const providersResult = await getGitProviders();
  const providers = providersResult.success ? (providersResult.data ?? []) : [];

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/${lang}/webhooks`}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-1 size-4" />
          {dict.webhooks.form.back}
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">
          {dict.webhooks.newTitle}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.webhooks.newDescription}
        </p>
      </div>

      <WebhookForm lang={lang} providers={providers} mode="create" />
    </div>
  );
}
