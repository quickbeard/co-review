import {
  GitBranch,
  FolderGit2,
  Server,
  ClipboardList,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface StatCardProps {
  title: string
  value: string | number
  description?: string
  icon: React.ComponentType<{ className?: string }>
  className?: string
}

function StatCard({ title, value, description, icon: Icon, className }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-background p-6 shadow-sm",
        className
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
  )
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Welcome to CoReview</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your code reviews and AI-powered PR analysis from one place.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Git Providers"
          value={0}
          description="Connected providers"
          icon={GitBranch}
        />
        <StatCard
          title="Repositories"
          value={0}
          description="Tracked repos"
          icon={FolderGit2}
        />
        <StatCard
          title="LLM Servers"
          value={0}
          description="Active servers"
          icon={Server}
        />
        <StatCard
          title="Reviews"
          value={0}
          description="Total reviews"
          icon={ClipboardList}
        />
      </div>

      <div className="rounded-lg border border-border bg-background p-6">
        <h2 className="text-lg font-semibold text-foreground">Getting Started</h2>
        <p className="mt-2 text-muted-foreground">
          To begin using CoReview, follow these steps:
        </p>
        <ol className="mt-4 list-inside list-decimal space-y-2 text-muted-foreground">
          <li>Connect a Git provider (GitHub, GitLab, etc.)</li>
          <li>Add repositories you want to track</li>
          <li>Configure an LLM server for AI-powered reviews</li>
          <li>Set up review contexts to customize analysis</li>
        </ol>
      </div>
    </div>
  )
}
