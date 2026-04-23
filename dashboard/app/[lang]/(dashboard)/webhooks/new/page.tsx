// Legacy "new webhook" route. Callers no longer pick the provider here -
// they visit a provider's Webhooks tab and use its "Add Webhook" button.
// Redirect to the provider list so the user can choose one first.

import { redirect } from "next/navigation";

export default async function LegacyNewWebhookPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  redirect(`/${lang}/git-providers`);
}
