import { Badge } from "@/components/ui/badge";
import type { GitProviderType } from "@/lib/api/types";

const providerColors: Record<GitProviderType, string> = {
  github: "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900",
  gitlab: "bg-orange-600 text-white",
  bitbucket: "bg-blue-600 text-white",
  azure_devops: "bg-blue-500 text-white",
  gitea: "bg-green-600 text-white",
  gerrit: "bg-teal-600 text-white",
};

const providerLabels: Record<GitProviderType, string> = {
  github: "GitHub",
  gitlab: "GitLab",
  bitbucket: "Bitbucket",
  azure_devops: "Azure DevOps",
  gitea: "Gitea",
  gerrit: "Gerrit",
};

interface ProviderTypeBadgeProps {
  type: GitProviderType;
}

export function ProviderTypeBadge({ type }: ProviderTypeBadgeProps) {
  return (
    <Badge variant="outline" className={providerColors[type]}>
      {providerLabels[type]}
    </Badge>
  );
}
