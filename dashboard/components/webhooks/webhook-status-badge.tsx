import { Badge } from "@/components/ui/badge";
import type { WebhookRegistrationStatus } from "@/lib/api/webhooks";
import type { Dictionary } from "@/app/dictionaries";

// Map a webhook lifecycle status to the badge variant that best communicates
// it. Keeping this out of the list component keeps the table markup lean.
const STATUS_VARIANT: Record<
  WebhookRegistrationStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "secondary",
  registered: "default",
  failed: "destructive",
  deleted: "outline",
};

interface WebhookStatusBadgeProps {
  status: WebhookRegistrationStatus;
  dict: Dictionary;
}

export function WebhookStatusBadge({ status, dict }: WebhookStatusBadgeProps) {
  const label = dict.webhooks.status[status] ?? status;
  return <Badge variant={STATUS_VARIANT[status]}>{label}</Badge>;
}
