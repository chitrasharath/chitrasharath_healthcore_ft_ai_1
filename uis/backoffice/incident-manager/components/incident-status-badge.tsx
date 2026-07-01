import { STATUS_BADGE_CLASSES, STATUSES } from "@backoffice/incident-manager/lib/constants";

type IncidentStatusBadgeProps = {
  status: string;
};

export const IncidentStatusBadge = ({ status }: IncidentStatusBadgeProps) => {
  const label = STATUSES.find((s) => s.value === status)?.label ?? status;
  const className = STATUS_BADGE_CLASSES[status] ?? STATUS_BADGE_CLASSES.discarded;
  return <span className={className}>{label}</span>;
};
