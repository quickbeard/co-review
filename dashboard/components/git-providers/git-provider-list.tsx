"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { MoreHorizontal, Pencil, Trash2, Power, PowerOff } from "lucide-react";
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
import { ProviderTypeBadge } from "./provider-type-badge";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  deleteGitProvider,
  toggleGitProviderStatus,
} from "@/lib/api/git-providers";
import type { GitProvider } from "@/lib/api/types";

interface GitProviderListProps {
  providers: GitProvider[];
  lang: string;
}

export function GitProviderList({ providers, lang }: GitProviderListProps) {
  const dict = useDictionary();
  const router = useRouter();

  async function handleDelete(id: number, name: string) {
    if (!confirm(dict.gitProviders.deleteConfirm.replace("{name}", name))) {
      return;
    }

    const result = await deleteGitProvider(id);
    if (result.success) {
      router.refresh();
    } else {
      alert(result.error || "Failed to delete provider");
    }
  }

  async function handleToggleStatus(id: number, currentStatus: boolean) {
    const result = await toggleGitProviderStatus(id, !currentStatus);
    if (result.success) {
      router.refresh();
    } else {
      alert(result.error || "Failed to update status");
    }
  }

  if (providers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-8 text-center">
        <h3 className="text-lg font-medium text-foreground">
          {dict.gitProviders.empty.title}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {dict.gitProviders.empty.description}
        </p>
        <Link href={`/${lang}/git-providers/new`} className="mt-4">
          <Button>{dict.gitProviders.addProvider}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{dict.gitProviders.table.name}</TableHead>
            <TableHead>{dict.gitProviders.table.type}</TableHead>
            <TableHead>{dict.gitProviders.table.status}</TableHead>
            <TableHead>{dict.gitProviders.table.createdAt}</TableHead>
            <TableHead className="w-[70px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {providers.map((provider) => (
            <TableRow key={provider.id}>
              <TableCell className="font-medium">{provider.name}</TableCell>
              <TableCell>
                <ProviderTypeBadge type={provider.type} />
              </TableCell>
              <TableCell>
                <Badge variant={provider.isActive ? "default" : "secondary"}>
                  {provider.isActive
                    ? dict.gitProviders.table.active
                    : dict.gitProviders.table.inactive}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {new Date(provider.createdAt).toLocaleDateString()}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
                    <MoreHorizontal className="h-4 w-4" />
                    <span className="sr-only">
                      {dict.gitProviders.table.actions}
                    </span>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem>
                      <Link
                        href={`/${lang}/git-providers/${provider.id}/edit`}
                        className="flex items-center w-full"
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        {dict.gitProviders.actions.edit}
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
                          {dict.gitProviders.actions.disable}
                        </>
                      ) : (
                        <>
                          <Power className="mr-2 h-4 w-4" />
                          {dict.gitProviders.actions.enable}
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(provider.id, provider.name)}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      {dict.gitProviders.actions.delete}
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
