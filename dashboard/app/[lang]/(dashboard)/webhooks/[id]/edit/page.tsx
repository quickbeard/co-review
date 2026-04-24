// Legacy edit URL. Look up the webhook, then redirect to the provider-
// scoped edit page so the user always edits within the right provider's
// context. Unknown webhook ids fall back to the provider list.

import { redirect } from "next/navigation";

import { getWebhook } from "@/lib/api/webhooks";

export default async function LegacyEditWebhookPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  const result = await getWebhook(id);
  if (!result.success || !result.data) {
    redirect(`/${lang}/git-providers`);
  }
  const { git_provider_id, id: webhookId } = result.data!;
  redirect(
    `/${lang}/git-providers/${git_provider_id}/webhooks/${webhookId}/edit`,
  );
}
