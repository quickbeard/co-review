import { GitBranch, FolderGit2, Server, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  className?: string;
}

function StatCard({
  title,
  value,
  description,
  icon: Icon,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-background p-6 shadow-sm",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-foreground">{value}</p>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        <div className="rounded-full bg-primary/10 p-3">
          <Icon className="size-6 text-primary" />
        </div>
      </div>
    </div>
  );
}

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;

  if (!hasLocale(lang)) {
    notFound();
  }

  const dict = await getDictionary(lang);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          {dict.dashboard.welcome}
        </h1>
        <p className="mt-1 text-muted-foreground">{dict.dashboard.description}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title={dict.dashboard.gitProviders}
          value={0}
          description={dict.dashboard.connectedProviders}
          icon={GitBranch}
        />
        <StatCard
          title={dict.dashboard.repositories}
          value={0}
          description={dict.dashboard.trackedRepos}
          icon={FolderGit2}
        />
        <StatCard
          title={dict.dashboard.llmServers}
          value={0}
          description={dict.dashboard.activeServers}
          icon={Server}
        />
        <StatCard
          title={dict.dashboard.reviews}
          value={0}
          description={dict.dashboard.totalReviews}
          icon={ClipboardList}
        />
      </div>

      <div className="rounded-lg border border-border bg-background p-6">
        <h2 className="text-lg font-semibold text-foreground">
          {dict.dashboard.gettingStarted}
        </h2>
        <p className="mt-2 text-muted-foreground">
          {dict.dashboard.gettingStartedDesc}
        </p>
        <ol className="mt-4 list-inside list-decimal space-y-2 text-muted-foreground">
          <li>{dict.dashboard.step1}</li>
          <li>{dict.dashboard.step2}</li>
          <li>{dict.dashboard.step3}</li>
          <li>{dict.dashboard.step4}</li>
        </ol>
      </div>
    </div>
  );
}
