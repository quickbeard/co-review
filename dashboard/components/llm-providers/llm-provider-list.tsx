"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  MoreHorizontal,
  Pencil,
  Trash2,
  Power,
  PowerOff,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { LLMProviderTypeBadge } from "./provider-type-badge";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  deleteLLMProvider,
  toggleLLMProviderStatus,
  setDefaultLLMProvider,
} from "@/lib/api/llm-providers";
import type { LLMProvider } from "@/lib/api/llm-provider-types";

interface LLMProviderListProps {
  providers: LLMProvider[];
  lang: string;
}

export function LLMProviderList({ providers, lang }: LLMProviderListProps) {
  const dict = useDictionary();
  const router = useRouter();

  async function handleDelete(id: number, name: string) {
    if (!confirm(dict.llmProviders.deleteConfirm.replace("{name}", name))) {
      return;
    }

    const result = await deleteLLMProvider(id);
    if (result.success) {
      router.refresh();
    } else {
      alert(result.error || "Failed to delete provider");
    }
  }

  async function handleToggleStatus(id: number, currentStatus: boolean) {
    const result = await toggleLLMProviderStatus(id, !currentStatus);
    if (result.success) {
      router.refresh();
    } else {
      alert(result.error || "Failed to update status");
    }
  }

  async function handleSetDefault(id: number) {
    const result = await setDefaultLLMProvider(id);
    if (result.success) {
      router.refresh();
    } else {
      alert(result.error || "Failed to set as default");
    }
  }

  if (providers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-8 text-center">
        <h3 className="text-lg font-medium text-foreground">
          {dict.llmProviders.empty.title}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {dict.llmProviders.empty.description}
        </p>
        <Link href={`/${lang}/llm-providers/new`} className="mt-4">
          <Button>{dict.llmProviders.addProvider}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{dict.llmProviders.table.name}</TableHead>
            <TableHead>{dict.llmProviders.table.type}</TableHead>
            <TableHead>{dict.llmProviders.table.status}</TableHead>
            <TableHead>{dict.llmProviders.table.default}</TableHead>
            <TableHead>{dict.llmProviders.table.createdAt}</TableHead>
            <TableHead className="w-[70px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {providers.map((provider) => (
            <TableRow key={provider.id}>
              <TableCell className="font-medium">{provider.name}</TableCell>
              <TableCell>
                <LLMProviderTypeBadge type={provider.type} />
              </TableCell>
              <TableCell>
                <Badge variant={provider.isActive ? "default" : "secondary"}>
                  {provider.isActive
                    ? dict.llmProviders.table.active
                    : dict.llmProviders.table.inactive}
                </Badge>
              </TableCell>
              <TableCell>
                {provider.isDefault && (
                  <Badge variant="outline" className="gap-1">
                    <Star className="h-3 w-3 fill-current" />
                    {dict.llmProviders.table.defaultBadge}
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {new Date(provider.createdAt).toLocaleDateString()}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
                    <MoreHorizontal className="h-4 w-4" />
                    <span className="sr-only">
                      {dict.llmProviders.table.actions}
                    </span>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem>
                      <Link
                        href={`/${lang}/llm-providers/${provider.id}/edit`}
                        className="flex items-center w-full"
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        {dict.llmProviders.actions.edit}
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleToggleStatus(provider.id, provider.isActive)
                      }
                    >
                      {provider.isActive ? (
                        <>
                          <PowerOff className="mr-2 h-4 w-4" />
                          {dict.llmProviders.actions.disable}
                        </>
                      ) : (
                        <>
                          <Power className="mr-2 h-4 w-4" />
                          {dict.llmProviders.actions.enable}
                        </>
                      )}
                    </DropdownMenuItem>
                    {!provider.isDefault && (
                      <DropdownMenuItem
                        onClick={() => handleSetDefault(provider.id)}
                      >
                        <Star className="mr-2 h-4 w-4" />
                        {dict.llmProviders.actions.setDefault}
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem
                      onClick={() => handleDelete(provider.id, provider.name)}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      {dict.llmProviders.actions.delete}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
