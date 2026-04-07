"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Globe } from "lucide-react";
import { locales, type Locale } from "@/lib/i18n/config";
import { cn } from "@/lib/utils";

const localeNames: Record<Locale, string> = {
  "en-US": "English (US)",
  vi: "Tiếng Việt",
};

export function LocaleSwitcher() {
  const pathname = usePathname();
  const router = useRouter();

  // Extract current locale from pathname
  const currentLocale = pathname.split("/")[1] as Locale;
  const pathWithoutLocale = pathname.split("/").slice(2).join("/");

  const switchLocale = (newLocale: Locale) => {
    const newPath = `/${newLocale}${pathWithoutLocale ? `/${pathWithoutLocale}` : ""}`;
    router.push(newPath);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          "disabled:pointer-events-none disabled:opacity-50",
          "hover:bg-accent hover:text-accent-foreground",
          "size-8",
        )}
        aria-label="Switch language"
      >
        <Globe className="size-5" />
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        {locales.map((locale) => (
          <DropdownMenuItem
            key={locale}
            onClick={() => switchLocale(locale)}
            className={currentLocale === locale ? "bg-accent" : ""}
          >
            {localeNames[locale]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
