import { locales } from "@/lib/i18n/config";
import { LangUpdater } from "@/components/lang-updater";

export async function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export default async function LangLayout({
  children,
  params,
}: LayoutProps<"/[lang]">) {
  const { lang } = await params;

  return (
    <>
      <LangUpdater lang={lang} />
      {children}
    </>
  );
}
