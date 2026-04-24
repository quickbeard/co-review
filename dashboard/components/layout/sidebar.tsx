"use client";

// Dashboard sidebar. Top-level items are rendered as links; items with
// `children` become collapsible groups whose open/closed state is derived
// from the current route (so users always see where they are).

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  BarChart3,
  GitBranch,
  Brain,
  Lightbulb,
  Settings,
  Zap,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import type { LucideIcon } from "lucide-react";

type NavKey = keyof ReturnType<typeof useDictionary>["nav"];

interface NavChild {
  nameKey: NavKey;
  href: string;
  icon?: LucideIcon;
}

interface NavItem {
  nameKey: NavKey;
  // Top-level href. Either this or `children` must be set. When both are set
  // the parent row becomes a link *and* a disclosure (clicking anywhere on the
  // row expands the group; a separate chevron button toggles expand/collapse).
  href?: string;
  icon: LucideIcon;
  children?: NavChild[];
}

const navigation: NavItem[] = [
  { nameKey: "overview", href: "/", icon: LayoutDashboard },
  { nameKey: "analytics", href: "/analytics", icon: BarChart3 },
  // Webhooks now live nested under each Git Provider (see the
  // /git-providers/{id}/webhooks tab). The top-level /webhooks route still
  // redirects to /git-providers so existing bookmarks keep working.
  { nameKey: "gitProviders", href: "/git-providers", icon: GitBranch },
  { nameKey: "llmProviders", href: "/llm-providers", icon: Brain },
  { nameKey: "learnings", href: "/learnings", icon: Lightbulb },
  {
    nameKey: "settings",
    href: "/settings",
    icon: Settings,
    children: [
      { nameKey: "automation", href: "/settings/automation", icon: Zap },
      {
        nameKey: "knowledgeBase",
        href: "/settings/knowledge-base",
        icon: BookOpen,
      },
    ],
  },
];

/** Is this row's href active for the given pathname (with locale stripped). */
function isHrefActive(href: string, pathWithoutLocale: string): boolean {
  if (href === "/") return pathWithoutLocale === "" || pathWithoutLocale === "/";
  return (
    pathWithoutLocale === href || pathWithoutLocale.startsWith(`${href}/`)
  );
}

/** Does any child of this parent match the current pathname? */
function hasActiveChild(item: NavItem, pathWithoutLocale: string): boolean {
  if (!item.children?.length) return false;
  return item.children.some((c) => isHrefActive(c.href, pathWithoutLocale));
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
}

export function Sidebar({ collapsed, onToggle, className }: SidebarProps) {
  const pathname = usePathname();
  const dict = useDictionary();

  const locale = pathname.split("/")[1];
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
        {navigation.map((item) => (
          <SidebarNavEntry
            key={item.nameKey}
            item={item}
            locale={locale}
            pathWithoutLocale={pathWithoutLocale}
            collapsed={collapsed}
          />
        ))}
      </nav>
    </aside>
  );
}

interface SidebarNavEntryProps {
  item: NavItem;
  locale: string;
  pathWithoutLocale: string;
  collapsed: boolean;
  onNavigate?: () => void;
}

/**
 * Renders either a flat link or a collapsible group for nested children.
 *
 * Expansion rules:
 * - Groups auto-expand when a child matches the current pathname, so users
 *   always see where they are without re-clicking.
 * - Users can manually toggle via the chevron without navigating.
 * - When the sidebar is `collapsed` (icon-only), children are hidden; the
 *   parent row links to the hub page so users can still navigate into the
 *   group one click at a time.
 */
function SidebarNavEntry({
  item,
  locale,
  pathWithoutLocale,
  collapsed,
  onNavigate,
}: SidebarNavEntryProps) {
  const dict = useDictionary();
  const Icon = item.icon;
  const name = dict.nav[item.nameKey];
  const hasChildren = !!item.children?.length;
  const childActive = hasActiveChild(item, pathWithoutLocale);
  const selfActive = item.href
    ? isHrefActive(item.href, pathWithoutLocale)
    : false;
  const active = selfActive || childActive;

  // Initial expanded state follows the current route; later it's user-owned.
  const [expanded, setExpanded] = useState<boolean>(childActive);
  useEffect(() => {
    if (childActive) setExpanded(true);
  }, [childActive]);

  if (!hasChildren) {
    const href = item.href ?? "#";
    const localizedHref = `/${locale}${href === "/" ? "" : href}`;
    return (
      <Link
        href={localizedHref}
        onClick={onNavigate}
        className={cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          selfActive
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
  }

  // Collapsed sidebar: render as a simple link to the parent hub. Users can
  // expand the sidebar to see children. Avoids complex popover UI for now.
  if (collapsed && item.href) {
    const localizedHref = `/${locale}${item.href}`;
    return (
      <Link
        href={localizedHref}
        onClick={onNavigate}
        className={cn(
          "flex items-center justify-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
          selfActive || childActive
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
        title={name}
      >
        <Icon className="size-5 shrink-0" />
      </Link>
    );
  }

  // Expanded sidebar: parent row = link to hub + chevron toggle button.
  const parentHref = item.href ? `/${locale}${item.href}` : "#";

  return (
    <div>
      <div
        className={cn(
          "group flex items-center gap-1 rounded-md pr-1 text-sm font-medium transition-colors",
          active
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        {item.href ? (
          <Link
            href={parentHref}
            onClick={onNavigate}
            className={cn(
              "flex flex-1 items-center gap-3 rounded-md px-3 py-2",
              selfActive && !childActive ? "text-primary" : "",
            )}
          >
            <Icon className="size-5 shrink-0" />
            <span className="flex-1">{name}</span>
          </Link>
        ) : (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex flex-1 items-center gap-3 rounded-md px-3 py-2 text-left"
          >
            <Icon className="size-5 shrink-0" />
            <span className="flex-1">{name}</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label={
            expanded
              ? dict.sidebar.collapseSidebar
              : dict.sidebar.expandSidebar
          }
          className="rounded-md p-1 hover:bg-muted/80"
        >
          <ChevronDown
            className={cn(
              "size-4 transition-transform",
              expanded ? "rotate-0" : "-rotate-90",
            )}
          />
        </button>
      </div>

      {expanded && (
        <ul className="mt-1 space-y-1 border-l border-border/60 pl-3">
          {item.children!.map((child) => {
            const ChildIcon = child.icon;
            const childIsActive = isHrefActive(
              child.href,
              pathWithoutLocale,
            );
            const localizedChildHref = `/${locale}${child.href}`;
            return (
              <li key={child.nameKey}>
                <Link
                  href={localizedChildHref}
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    childIsActive
                      ? "bg-primary/10 font-medium text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  {ChildIcon ? (
                    <ChildIcon className="size-4 shrink-0" />
                  ) : (
                    <span className="size-4 shrink-0" />
                  )}
                  <span>{dict.nav[child.nameKey]}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

interface MobileSidebarProps {
  open: boolean;
  onClose: () => void;
}

export function MobileSidebar({ open, onClose }: MobileSidebarProps) {
  const pathname = usePathname();
  const dict = useDictionary();

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
          {navigation.map((item) => (
            <SidebarNavEntry
              key={item.nameKey}
              item={item}
              locale={locale}
              pathWithoutLocale={pathWithoutLocale}
              collapsed={false}
              onNavigate={onClose}
            />
          ))}
        </nav>
      </aside>
    </>
  );
}
