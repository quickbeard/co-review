"use client";

import { Menu, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/ui/mode-toggle";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { useDictionary } from "@/lib/i18n/dictionary-context";

interface HeaderProps {
  onMenuClick: () => void;
  className?: string;
}

export function Header({ onMenuClick, className }: HeaderProps) {
  const dict = useDictionary();

  return (
    <header
      className={cn(
        "flex h-14 items-center justify-between border-b border-border bg-background px-4",
        className,
      )}
    >
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onMenuClick}
          className="lg:hidden"
          aria-label={dict.header.openMenu}
        >
          <Menu className="size-5" />
        </Button>
        <h1 className="text-lg font-semibold text-foreground lg:hidden">
          {dict.common.appName}
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <LocaleSwitcher />
        <ModeToggle />
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={dict.header.userMenu}
        >
          <User className="size-5" />
        </Button>
      </div>
    </header>
  );
}
