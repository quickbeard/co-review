import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, BookOpen, Zap } from "lucide-react";

import { hasLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/app/dictionaries";

/**
 * Settings hub. Landing page for the nested /settings/* tree.
 * Sections (cards) should stay in sync with the sidebar's "Settings" children
 * in `components/layout/sidebar.tsx` so the two stay at feature parity.
 */
export default async function SettingsPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const t = dict.settings;

  const sections = [
    {
      key: "automation" as const,
      href: `/${lang}/settings/automation`,
      icon: Zap,
      title: t.sections.automation.title,
      description: t.sections.automation.description,
    },
    {
      key: "knowledgeBase" as const,
      href: `/${lang}/settings/knowledge-base`,
      icon: BookOpen,
      title: t.sections.knowledgeBase.title,
      description: t.sections.knowledgeBase.description,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t.title}</h1>
        <p className="mt-1 text-muted-foreground">{t.description}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {sections.map(({ key, href, icon: Icon, title, description }) => (
          <Link
            key={key}
            href={href}
            className="group flex items-start gap-4 rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary hover:bg-muted/50"
          >
            <span className="rounded-md bg-primary/10 p-2 text-primary">
              <Icon className="size-5" />
            </span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-foreground">
                  {title}
                </h2>
                <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {description}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
