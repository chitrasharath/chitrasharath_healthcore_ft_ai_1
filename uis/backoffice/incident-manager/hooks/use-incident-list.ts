"use client";

import { useCallback, useEffect, useState } from "react";

import { listIncidents, updateIncidentStatus } from "@backoffice/incident-manager/lib/incidents-api";
import type { Incident, IncidentFilters } from "@backoffice/incident-manager/types/incidents";

export const useIncidentList = () => {
  const [filters, setFilters] = useState<IncidentFilters>({});
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listIncidents(filters);
      setIncidents(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load incidents");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  const changeStatus = async (id: number, status: string) => {
    const previous = incidents;
    setIncidents((rows) => rows.map((r) => (r.id === id ? { ...r, status } : r)));
    setStatusError(null);
    try {
      const updated = await updateIncidentStatus(id, status);
      setIncidents((rows) => rows.map((r) => (r.id === id ? updated : r)));
    } catch (err: unknown) {
      setIncidents(previous);
      setStatusError(err instanceof Error ? err.message : "Status update failed");
    }
  };

  return { filters, setFilters, incidents, loading, error, statusError, load, changeStatus };
};
