import { parseApiDateTime } from "@backoffice/incident-manager/lib/format";
import type { Incident } from "@backoffice/incident-manager/types/incidents";

export type IncidentSortKey =
  | "title"
  | "category"
  | "status"
  | "origin"
  | "branch"
  | "created_at"
  | "updated_at";

export type SortDirection = "asc" | "desc";

export const INCIDENT_SORT_COLUMNS: { key: IncidentSortKey; label: string }[] = [
  { key: "title", label: "Title" },
  { key: "category", label: "Category" },
  { key: "status", label: "Status" },
  { key: "origin", label: "Origin" },
  { key: "branch", label: "Branch" },
  { key: "created_at", label: "Created At" },
  { key: "updated_at", label: "Updated At" },
];

const compareValues = (left: string | number, right: string | number): number => {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
};

export const sortIncidents = (
  incidents: Incident[],
  key: IncidentSortKey,
  direction: SortDirection,
): Incident[] => {
  const sorted = [...incidents].sort((a, b) => {
    let result = 0;
    if (key === "created_at" || key === "updated_at") {
      result = compareValues(
        parseApiDateTime(a[key]).getTime(),
        parseApiDateTime(b[key]).getTime(),
      );
    } else {
      result = a[key].localeCompare(b[key]);
    }
    return direction === "asc" ? result : -result;
  });
  return sorted;
};
