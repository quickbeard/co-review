export const dynamic = "force-dynamic";

import Link from "next/link";
import { Plus } from "lucide-react";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  GitProviderActions,
  ProviderTypeBadge,
} from "@/components/git-providers";
import { getGitProviders } from "@/lib/actions/git-providers";

export default async function GitProvidersPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const providers = await getGitProviders();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {dict.gitProviders.title}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {dict.gitProviders.description}
          </p>
        </div>
        <Button>
          <Link
            href={`/${lang}/git-providers/new`}
            className="flex items-center gap-2"
          >
            <Plus className="size-4" />
            {dict.gitProviders.addProvider}
          </Link>
        </Button>
      </div>

      {providers.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <h3 className="text-lg font-medium text-foreground">
            {dict.gitProviders.emptyState.title}
          </h3>
          <p className="mt-2 text-muted-foreground">
            {dict.gitProviders.emptyState.description}
          </p>
          <Button className="mt-4">
            <Link
              href={`/${lang}/git-providers/new`}
              className="flex items-center gap-2"
            >
              <Plus className="size-4" />
              {dict.gitProviders.addProvider}
            </Link>
          </Button>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-background">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{dict.gitProviders.table.name}</TableHead>
                <TableHead>{dict.gitProviders.table.type}</TableHead>
                <TableHead>{dict.gitProviders.table.repositories}</TableHead>
                <TableHead>{dict.gitProviders.table.status}</TableHead>
                <TableHead className="w-12">
                  <span className="sr-only">
                    {dict.gitProviders.table.actions}
                  </span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {providers.map((provider) => (
                <TableRow key={provider.id}>
                  <TableCell>
                    <Link
                      href={`/${lang}/git-providers/${provider.id}`}
                      className="font-medium text-foreground hover:underline"
                    >
                      {provider.name}
                    </Link>
                    {provider.baseUrl && (
                      <p className="text-sm text-muted-foreground">
                        {provider.baseUrl}
                      </p>
                    )}
                  </TableCell>
                  <TableCell>
                    <ProviderTypeBadge type={provider.type} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {provider._count.repositories}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={provider.isActive ? "default" : "secondary"}
                    >
                      {provider.isActive
                        ? dict.gitProviders.status.active
                        : dict.gitProviders.status.inactive}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <GitProviderActions provider={provider} lang={lang} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
