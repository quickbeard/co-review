"use client";

// Tab strip that sits at the top of the per-provider edit scope. Each tab is
// its own route so deep-links, the browser back button, and the Next.js
// router prefetch all work exactly like the rest of the dashboard.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/lib/i18n/dictionary-context";

interface ProviderTabsNavProps {
  lang: string;
  providerId: number;
  // Number of webhook registrations already stored for this provider; drives
  // the small counter in the "Repository Webhooks" tab. Hidden when 0 to
  // keep the nav quiet until the user actually has registrations.
  webhookCount?: number;
}

export function ProviderTabsNav({
  lang,
  providerId,
  webhookCount,
}: ProviderTabsNavProps) {
  const dict = useDictionary();
  const pathname = usePathname();
  const base = `/${lang}/git-providers/${providerId}`;

  const tabs = [
    {
      key: "credentials",
      href: `${base}/edit`,
      label: dict.gitProviders.tabs.credentials,
    },
    {
      key: "webhooks",
      href: `${base}/webhooks`,
      label: dict.gitProviders.tabs.webhooks,
    },
  ] as const;

  return (
    <nav
      aria-label={dict.gitProviders.tabs.ariaLabel}
      className="flex gap-1 border-b border-border"
    >
      {tabs.map((tab) => {
        const active =
          pathname === tab.href || pathname.startsWith(`${tab.href}/`);
        return (
          <Link
            key={tab.key}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "-mb-px inline-flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
            {tab.key === "webhooks" &&
              typeof webhookCount === "number" &&
              webhookCount > 0 && (
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-semibold",
                    active
                      ? "bg-primary/15 text-primary"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {webhookCount}
                </span>
              )}
          </Link>
        );
      })}
    </nav>
  );
}
