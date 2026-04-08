"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  nameKey: keyof ReturnType<typeof useDictionary>["nav"];
  href: string;
  icon: LucideIcon;
}

const navigation: NavItem[] = [
  { nameKey: "overview", href: "/", icon: LayoutDashboard },
  { nameKey: "settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
}

export function Sidebar({ collapsed, onToggle, className }: SidebarProps) {
  const pathname = usePathname();
  const dict = useDictionary();

  // Extract locale from pathname (e.g., /en-US/settings -> en-US)
  const locale = pathname.split("/")[1];
  // Get the path without locale prefix for active state matching
  const pathWithoutLocale = "/" + pathname.split("/").slice(2).join("/");

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-border bg-background transition-all duration-300",
        collapsed ? "w-16" : "w-64",
        className,
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-border px-4">
        {!collapsed && (
          <span className="text-lg font-semibold text-foreground">
            {dict.common.appName}
          </span>
        )}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggle}
          className={cn(collapsed && "mx-auto")}
          aria-label={
            collapsed
              ? dict.sidebar.expandSidebar
              : dict.sidebar.collapseSidebar
          }
        >
          {collapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navigation.map((item) => {
          const isActive =
            pathWithoutLocale === item.href ||
            (item.href === "/" && pathWithoutLocale === "");
          const Icon = item.icon;
          const name = dict.nav[item.nameKey];
          const localizedHref = `/${locale}${item.href === "/" ? "" : item.href}`;

          return (
            <Link
              key={item.nameKey}
              href={localizedHref}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
                collapsed && "justify-center px-2",
              )}
              title={collapsed ? name : undefined}
            >
              <Icon className="size-5 shrink-0" />
              {!collapsed && <span>{name}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

interface MobileSidebarProps {
  open: boolean;
  onClose: () => void;
}

export function MobileSidebar({ open, onClose }: MobileSidebarProps) {
  const pathname = usePathname();
  const dict = useDictionary();

  // Extract locale from pathname
  const locale = pathname.split("/")[1];
  const pathWithoutLocale = "/" + pathname.split("/").slice(2).join("/");

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 lg:hidden"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-background shadow-lg lg:hidden">
        <div className="flex h-14 items-center border-b border-border px-4">
          <span className="text-lg font-semibold text-foreground">
            {dict.common.appName}
          </span>
        </div>

        <nav className="space-y-1 p-2">
          {navigation.map((item) => {
            const isActive =
              pathWithoutLocale === item.href ||
              (item.href === "/" && pathWithoutLocale === "");
            const Icon = item.icon;
            const name = dict.nav[item.nameKey];
            const localizedHref = `/${locale}${item.href === "/" ? "" : item.href}`;

            return (
              <Link
                key={item.nameKey}
                href={localizedHref}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="size-5 shrink-0" />
                <span>{name}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
