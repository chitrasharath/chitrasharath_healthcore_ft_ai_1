"use client";

import {
  BRANCHES,
  CATEGORIES,
  ORIGINS,
  STATUSES,
} from "@backoffice/incident-manager/lib/constants";
import {
  trackFilterApplied,
  type FilterDimension,
} from "@backoffice/incident-manager/lib/filter-telemetry";
import type { IncidentFilters } from "@backoffice/incident-manager/types/incidents";

type IncidentListFiltersProps = {
  filters: IncidentFilters;
  onChange: (filters: IncidentFilters) => void;
};

const selectClass = "rounded-lg border border-slate-300 px-3 py-2 text-sm";

const applyFilter = (
  dimension: FilterDimension,
  value: string,
  filters: IncidentFilters,
  onChange: (filters: IncidentFilters) => void,
) => {
  const next = { ...filters, [dimension]: value || undefined };
  trackFilterApplied(dimension, value, next);
  onChange(next);
};

export const IncidentListFilters = ({ filters, onChange }: IncidentListFiltersProps) => (
  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Status</span>
      <select
        className={selectClass}
        value={filters.status ?? ""}
        onChange={(e) => applyFilter("status", e.target.value, filters, onChange)}
      >
        <option value="">All</option>
        {STATUSES.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </label>
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Origin</span>
      <select
        className={selectClass}
        value={filters.origin ?? ""}
        onChange={(e) => applyFilter("origin", e.target.value, filters, onChange)}
      >
        <option value="">All</option>
        {ORIGINS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Branch</span>
      <select
        className={selectClass}
        value={filters.branch ?? ""}
        onChange={(e) => applyFilter("branch", e.target.value, filters, onChange)}
      >
        <option value="">All</option>
        {BRANCHES.map((b) => (
          <option key={b.value} value={b.value}>
            {b.value}
          </option>
        ))}
      </select>
    </label>
    <label className="space-y-1 text-sm">
      <span className="font-medium text-slate-700">Category</span>
      <select
        className={selectClass}
        value={filters.category ?? ""}
        onChange={(e) => applyFilter("category", e.target.value, filters, onChange)}
      >
        <option value="">All</option>
        {CATEGORIES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
    </label>
  </div>
);
