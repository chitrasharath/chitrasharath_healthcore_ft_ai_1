import {
  BRANCHES,
  CATEGORIES,
  ORIGINS,
  STATUSES,
} from "@backoffice/incident-manager/lib/constants";
import type { IncidentFilters } from "@backoffice/incident-manager/types/incidents";

type IncidentListFiltersProps = {
  filters: IncidentFilters;
  onChange: (filters: IncidentFilters) => void;
};

const selectClass = "rounded-lg border border-slate-300 px-3 py-2 text-sm";

export const IncidentListFilters = ({ filters, onChange }: IncidentListFiltersProps) => (
  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Status</span>
      <select className={selectClass} value={filters.status ?? ""} onChange={(e) => onChange({ ...filters, status: e.target.value || undefined })}>
        <option value="">All</option>
        {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>
    </label>
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Origin</span>
      <select className={selectClass} value={filters.origin ?? ""} onChange={(e) => onChange({ ...filters, origin: e.target.value || undefined })}>
        <option value="">All</option>
        {ORIGINS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Branch</span>
      <select className={selectClass} value={filters.branch ?? ""} onChange={(e) => onChange({ ...filters, branch: e.target.value || undefined })}>
        <option value="">All</option>
        {BRANCHES.map((b) => <option key={b.value} value={b.value}>{b.value}</option>)}
      </select>
    </label>
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Category</span>
      <select className={selectClass} value={filters.category ?? ""} onChange={(e) => onChange({ ...filters, category: e.target.value || undefined })}>
        <option value="">All</option>
        {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    </label>
  </div>
);
