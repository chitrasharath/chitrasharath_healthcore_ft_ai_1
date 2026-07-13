import type { IncidentFilters } from "@backoffice/incident-manager/types/incidents";
import { track } from "@backoffice/shared/lib/telemetry";

export type FilterDimension = "status" | "origin" | "branch" | "category";

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

export const countActiveFilters = (filters: IncidentFilters): number =>
  [filters.status, filters.origin, filters.branch, filters.category].filter(Boolean).length;

export const trackFilterApplied = (
  dimension: FilterDimension,
  value: string,
  filters: IncidentFilters,
): void => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    track("incident_list_filter_applied", {
      filter_dimension: dimension,
      filter_value: value,
      active_filter_count: countActiveFilters(filters),
    });
  }, 500);
};

export const __clearFilterTelemetryDebounceForTests = (): void => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = null;
};
