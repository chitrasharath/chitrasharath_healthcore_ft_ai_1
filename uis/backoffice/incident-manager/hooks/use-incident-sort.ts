"use client";

import { useMemo, useState } from "react";

import {
  sortIncidents,
  type IncidentSortKey,
  type SortDirection,
} from "@backoffice/incident-manager/lib/sort-incidents";
import type { Incident } from "@backoffice/incident-manager/types/incidents";

export const useIncidentSort = (incidents: Incident[]) => {
  const [sortKey, setSortKey] = useState<IncidentSortKey>("created_at");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const toggleSort = (key: IncidentSortKey) => {
    if (key === sortKey) {
      setSortDirection((dir) => (dir === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDirection(key === "created_at" || key === "updated_at" ? "desc" : "asc");
  };

  const sortedIncidents = useMemo(
    () => sortIncidents(incidents, sortKey, sortDirection),
    [incidents, sortKey, sortDirection],
  );

  return { sortKey, sortDirection, toggleSort, sortedIncidents };
};
