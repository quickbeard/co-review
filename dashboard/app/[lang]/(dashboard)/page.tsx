import {
  GitBranch,
  FolderGit2,
  Server,
  Lightbulb,
  GitPullRequest,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getDictionary } from "@/app/dictionaries";
import { hasLocale } from "@/lib/i18n/config";
import { notFound } from "next/navigation";

import { getGitProviders } from "@/lib/api/git-providers";
import { getLLMProviders } from "@/lib/api/llm-providers";
import { getLearnings } from "@/lib/api/learnings";
import { getWebhooks } from "@/lib/api/webhooks";
import { getPRReviewActivityStats } from "@/lib/api/pr-review-activities";

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

  // Fetch counters in parallel. Any individual failure defaults to 0 so the
  // dashboard still renders if a single API call is broken (e.g. the
  // learnings endpoint is disabled). We only need the totals here, so we
  // ask the learnings endpoint for a single item: since 0005 the backend
  // computes `total` against the full population, independent of `limit`.
  const [
    gitProvidersRes,
    llmProvidersRes,
    webhooksRes,
    learningsRes,
    reviewStatsRes,
  ] = await Promise.all([
    getGitProviders(),
    getLLMProviders(),
    getWebhooks(),
    getLearnings({ limit: 1 }),
    getPRReviewActivityStats(),
  ]);

  const gitProviders = gitProvidersRes.success
    ? (gitProvidersRes.data ?? [])
    : [];
  const activeGitProviders = gitProviders.filter((p) => p.isActive).length;

  const llmProviders = llmProvidersRes.success
    ? (llmProvidersRes.data ?? [])
    : [];
  const activeLlmProviders = llmProviders.filter((p) => p.isActive).length;

  const webhooks = webhooksRes.success ? (webhooksRes.data ?? []) : [];

  // "Repositories" is synthesized from two sources because neither alone
  // captures every repo PR-Agent interacts with:
  //   - webhook registrations cover PAT-mode repos we've explicitly wired
  //   - learnings.repos covers any repo where a comment or capture happened
  //     (includes GitHub App repos that never get per-repo webhooks)
  const repoSet = new Set<string>();
  for (const w of webhooks) {
    if (w.repo) repoSet.add(w.repo);
  }
  if (learningsRes.success && learningsRes.data?.repos) {
    for (const r of learningsRes.data.repos) {
      if (r) repoSet.add(r);
    }
  }
  const repoCount = repoSet.size;

  const learningsTotal =
    learningsRes.success && learningsRes.data
      ? learningsRes.data.total
      : 0;

  const reviewStats = reviewStatsRes.success ? reviewStatsRes.data : null;
  // Prefer the "review tools" breakdown (PRs that received /review, /improve
  // or /describe) for the headline number. Fall back to all-unique-PRs when
  // the audit log is empty-but-populated with non-review tools only.
  const reviewedPRs = reviewStats
    ? reviewStats.reviewToolsUniquePrs || reviewStats.uniquePrs
    : 0;
  const reviewInvocations = reviewStats?.totalInvocations ?? 0;

  // Treat the stats endpoint's repo count as a floor — we don't get repo
  // names there, but we want the Repositories card to reflect any repo
  // we've captured audit evidence for, even without a webhook row yet.
  const repoCountWithReviews = Math.max(
    repoCount,
    reviewStats?.uniqueRepos ?? 0,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          {dict.dashboard.welcome}
        </h1>
        <p className="mt-1 text-muted-foreground">
          {dict.dashboard.description}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <StatCard
          title={dict.dashboard.gitProviders}
          value={gitProviders.length}
          description={dict.dashboard.connectedProviders.replace(
            "{n}",
            String(activeGitProviders),
          )}
          icon={GitBranch}
        />
        <StatCard
          title={dict.dashboard.repositories}
          value={repoCountWithReviews}
          description={dict.dashboard.trackedRepos}
          icon={FolderGit2}
        />
        <StatCard
          title={dict.dashboard.llmServers}
          value={llmProviders.length}
          description={dict.dashboard.activeServers.replace(
            "{n}",
            String(activeLlmProviders),
          )}
          icon={Server}
        />
        <StatCard
          title={dict.dashboard.reviewedPRs}
          value={reviewedPRs}
          description={dict.dashboard.reviewedPRsDesc.replace(
            "{n}",
            String(reviewInvocations),
          )}
          icon={GitPullRequest}
        />
        <StatCard
          title={dict.dashboard.learnings}
          value={learningsTotal}
          description={dict.dashboard.capturedLearnings}
          icon={Lightbulb}
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
