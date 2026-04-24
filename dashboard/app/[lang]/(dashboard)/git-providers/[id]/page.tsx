// Bare /git-providers/{id} redirects to the Credentials tab. Keeps the URL
// shape predictable so the breadcrumb/tab nav always has a concrete tab
// highlighted.

import { redirect } from "next/navigation";

export default async function GitProviderDetailIndex({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  redirect(`/${lang}/git-providers/${id}/edit`);
}
