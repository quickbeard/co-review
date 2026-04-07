"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontal, Pencil, Trash2, Power, PowerOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDictionary } from "@/lib/i18n/dictionary-context";
import {
  deleteGitProvider,
  toggleGitProviderStatus,
} from "@/lib/actions/git-providers";

interface GitProviderActionsProps {
  provider: {
    id: string;
    name: string;
    isActive: boolean;
  };
  lang: string;
}

export function GitProviderActions({
  provider,
  lang,
}: GitProviderActionsProps) {
  const dict = useDictionary();
  const router = useRouter();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pending, setPending] = useState(false);

  async function handleDelete() {
    setPending(true);
    const result = await deleteGitProvider(provider.id);
    setPending(false);

    if (result.success) {
      setDeleteDialogOpen(false);
      router.refresh();
    }
  }

  async function handleToggleStatus() {
    setPending(true);
    await toggleGitProviderStatus(provider.id, !provider.isActive);
    setPending(false);
    router.refresh();
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
          <MoreHorizontal className="size-4" />
          <span className="sr-only">{dict.gitProviders.actions.openMenu}</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem
            onClick={() => router.push(`/${lang}/git-providers/${provider.id}`)}
          >
            {dict.gitProviders.actions.viewDetails}
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() =>
              router.push(`/${lang}/git-providers/${provider.id}/edit`)
            }
          >
            <Pencil className="mr-2 size-4" />
            {dict.gitProviders.actions.edit}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleToggleStatus} disabled={pending}>
            {provider.isActive ? (
              <>
                <PowerOff className="mr-2 size-4" />
                {dict.gitProviders.actions.disable}
              </>
            ) : (
              <>
                <Power className="mr-2 size-4" />
                {dict.gitProviders.actions.enable}
              </>
            )}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setDeleteDialogOpen(true)}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 size-4" />
            {dict.gitProviders.actions.delete}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dict.gitProviders.deleteDialog.title}</DialogTitle>
            <DialogDescription>
              {dict.gitProviders.deleteDialog.description.replace(
                "{name}",
                provider.name,
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={pending}
            >
              {dict.gitProviders.deleteDialog.cancel}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={pending}
            >
              {pending
                ? dict.gitProviders.deleteDialog.deleting
                : dict.gitProviders.deleteDialog.confirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
