import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { GitProviderType } from "@/generated/prisma/client";

interface ProviderTypeBadgeProps {
  type: GitProviderType;
  className?: string;
}

const providerLabels: Record<GitProviderType, string> = {
  github: "GitHub",
  gitlab: "GitLab",
  bitbucket: "Bitbucket",
  azure_devops: "Azure DevOps",
  gitea: "Gitea",
  gerrit: "Gerrit",
};

const providerColors: Record<GitProviderType, string> = {
  github: "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900",
  gitlab: "bg-orange-500 text-white",
  bitbucket: "bg-blue-600 text-white",
  azure_devops: "bg-blue-500 text-white",
  gitea: "bg-green-600 text-white",
  gerrit: "bg-purple-600 text-white",
};

export function ProviderTypeBadge({ type, className }: ProviderTypeBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className={cn(
        "border-transparent font-medium",
        providerColors[type],
        className,
      )}
    >
      {providerLabels[type]}
    </Badge>
  );
}

export { providerLabels };
