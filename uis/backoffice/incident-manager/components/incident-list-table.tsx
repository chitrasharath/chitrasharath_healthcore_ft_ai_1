"use client";

import { formatIncidentDate } from "@backoffice/incident-manager/lib/format";
import {
  INCIDENT_SORT_COLUMNS,
  type IncidentSortKey,
  type SortDirection,
} from "@backoffice/incident-manager/lib/sort-incidents";
import { useIncidentTimezone } from "@backoffice/incident-manager/components/incident-timezone-context";
import { IncidentRowActions } from "@backoffice/incident-manager/components/incident-row-actions";
import { IncidentStatusCell } from "@backoffice/incident-manager/components/incident-status-cell";
import { SortableTh } from "@backoffice/incident-manager/components/sortable-th";
import type { Incident } from "@backoffice/incident-manager/types/incidents";

type IncidentListTableProps = {
  incidents: Incident[];
  sortKey: IncidentSortKey;
  sortDirection: SortDirection;
  onSort: (key: IncidentSortKey) => void;
  onStatusChange: (id: number, status: string) => void;
};

export const IncidentListTable = ({
  incidents,
  sortKey,
  sortDirection,
  onSort,
  onStatusChange,
}: IncidentListTableProps) => {
  const { timezone } = useIncidentTimezone();

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1040px] text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-center">
            {INCIDENT_SORT_COLUMNS.map((col) => (
              <SortableTh
                key={col.key}
                label={col.label}
                column={col.key}
                sortKey={sortKey}
                sortDirection={sortDirection}
                onSort={onSort}
              />
            ))}
            <th className="px-2 pb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((row) => (
            <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="px-2 py-3 text-left font-medium text-slate-900">{row.title}</td>
              <td className="px-2 py-3 text-left text-slate-700">{row.category}</td>
              <td className="px-2 py-3 text-left">
                <IncidentStatusCell id={row.id} status={row.status} onChange={onStatusChange} />
              </td>
              <td className="px-2 py-3 text-left text-slate-700">{row.origin}</td>
              <td className="px-2 py-3 text-left text-slate-700">{row.branch}</td>
              <td className="px-2 py-3 text-left text-slate-700">{formatIncidentDate(row.created_at, timezone)}</td>
              <td className="px-2 py-3 text-left text-slate-700">{formatIncidentDate(row.updated_at, timezone)}</td>
              <td className="px-2 py-3">
                <IncidentRowActions id={row.id} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
