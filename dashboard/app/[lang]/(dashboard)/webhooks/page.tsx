// Webhooks used to live as a standalone top-level page; they now live
// nested under each Git Provider. This redirect keeps old bookmarks and
// links working.

import { redirect } from "next/navigation";

export default async function LegacyWebhooksIndex({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  redirect(`/${lang}/git-providers`);
}
