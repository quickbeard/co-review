export const dynamic = "force-dynamic";

import Link from "next/link";
import { ArrowLeft, Pencil, FolderGit2 } from "lucide-react";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ProviderTypeBadge } from "@/components/git-providers";
import { getGitProvider } from "@/lib/actions/git-providers";

export default async function GitProviderDetailPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);
  const provider = await getGitProvider(id);

  if (!provider) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Link
            href={`/${lang}/git-providers`}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            {dict.gitProviders.backToList}
          </Link>
          <h1 className="mt-4 text-2xl font-bold text-foreground">
            {provider.name}
          </h1>
          <div className="mt-2 flex items-center gap-2">
            <ProviderTypeBadge type={provider.type} />
            <Badge variant={provider.isActive ? "default" : "secondary"}>
              {provider.isActive
                ? dict.gitProviders.status.active
                : dict.gitProviders.status.inactive}
            </Badge>
          </div>
        </div>
        <Button variant="outline">
          <Link
            href={`/${lang}/git-providers/${id}/edit`}
            className="flex items-center gap-2"
          >
            <Pencil className="size-4" />
            {dict.gitProviders.actions.edit}
          </Link>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{dict.gitProviders.detail.configuration}</CardTitle>
            <CardDescription>
              {dict.gitProviders.detail.configurationDescription}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                {dict.gitProviders.form.type}
              </dt>
              <dd className="mt-1 text-foreground">
                <ProviderTypeBadge type={provider.type} />
              </dd>
            </div>
            {provider.baseUrl && (
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  {dict.gitProviders.form.baseUrl}
                </dt>
                <dd className="mt-1 text-foreground">{provider.baseUrl}</dd>
              </div>
            )}
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                {dict.gitProviders.form.accessToken}
              </dt>
              <dd className="mt-1 font-mono text-sm text-muted-foreground">
                ••••••••••••
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                {dict.gitProviders.form.webhookSecret}
              </dt>
              <dd className="mt-1 font-mono text-sm text-muted-foreground">
                {provider.webhookSecret ? "••••••••••••" : "-"}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                {dict.gitProviders.detail.createdAt}
              </dt>
              <dd className="mt-1 text-foreground">
                {new Date(provider.createdAt).toLocaleDateString(lang, {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </dd>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderGit2 className="size-5" />
              {dict.gitProviders.detail.repositories}
            </CardTitle>
            <CardDescription>
              {dict.gitProviders.detail.repositoriesDescription}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {provider.repositories.length === 0 ? (
              <div className="py-6 text-center text-muted-foreground">
                {dict.gitProviders.detail.noRepositories}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{dict.gitProviders.detail.repoName}</TableHead>
                    <TableHead>{dict.gitProviders.detail.repoStatus}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {provider.repositories.map((repo) => (
                    <TableRow key={repo.id}>
                      <TableCell>
                        <span className="font-medium">{repo.fullName}</span>
                        <p className="text-sm text-muted-foreground">
                          {repo.defaultBranch}
                        </p>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={repo.isActive ? "default" : "secondary"}
                        >
                          {repo.isActive
                            ? dict.gitProviders.status.active
                            : dict.gitProviders.status.inactive}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
