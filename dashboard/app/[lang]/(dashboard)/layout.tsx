import { Shell } from "@/components/layout";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { DictionaryProvider } from "@/lib/i18n/dictionary-context";

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dictionary = await getDictionary(lang);

  return (
    <DictionaryProvider dictionary={dictionary}>
      <Shell>{children}</Shell>
    </DictionaryProvider>
  );
}
