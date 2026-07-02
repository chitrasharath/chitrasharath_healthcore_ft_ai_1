"use client";

import Link from "next/link";

import { CATEGORIES, ORIGINS, STATUSES } from "@backoffice/incident-manager/lib/constants";
import { formatIncidentDate } from "@backoffice/incident-manager/lib/format";
import { IncidentStatusBadge } from "@backoffice/incident-manager/components/incident-status-badge";
import { StatusBanner } from "@backoffice/incident-manager/components/status-banner";
import { useIncidentDetail } from "@backoffice/incident-manager/hooks/use-incident-detail";
import { useIncidentTimezone } from "@backoffice/incident-manager/components/incident-timezone-context";

type IncidentDetailProps = {
  incidentId: number;
};

const labelClass = "text-xs font-semibold uppercase tracking-wide text-slate-500";
const valueClass = "mt-1 text-sm text-slate-800";

export const IncidentDetail = ({ incidentId }: IncidentDetailProps) => {
  const { incident, loading, error } = useIncidentDetail(incidentId);
  const { timezone } = useIncidentTimezone();

  if (loading) return <p className="text-sm font-medium text-sky-800">Loading incident…</p>;
  if (error) return <StatusBanner variant="error" message={error} />;
  if (!incident) return null;

  const categoryLabel = CATEGORIES.find((c) => c.value === incident.category)?.label ?? incident.category;
  const originLabel = ORIGINS.find((o) => o.value === incident.origin)?.label ?? incident.origin;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <IncidentStatusBadge status={incident.status} />
        <Link href={`/incident-manager/${incidentId}/edit`} className="rounded-md bg-sky-700 px-4 py-2 text-sm font-bold text-white hover:bg-sky-800">
          Edit incident
        </Link>
      </div>
      <dl className="grid gap-4 sm:grid-cols-2">
        <DetailItem label="Title" value={incident.title} className="sm:col-span-2" />
        <DetailItem label="Description" value={incident.description} className="sm:col-span-2" />
        <DetailItem label="Category" value={categoryLabel} />
        <DetailItem label="Status" value={STATUSES.find((s) => s.value === incident.status)?.label ?? incident.status} />
        <DetailItem label="Origin" value={originLabel} />
        <DetailItem label="Branch" value={incident.branch} />
        <DetailItem label="Created at" value={formatIncidentDate(incident.created_at, timezone)} />
        <DetailItem label="Updated at" value={formatIncidentDate(incident.updated_at, timezone)} />
      </dl>
    </div>
  );
};

const DetailItem = ({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) => (
  <div className={className}>
    <dt className={labelClass}>{label}</dt>
    <dd className={valueClass}>{value}</dd>
  </div>
);
