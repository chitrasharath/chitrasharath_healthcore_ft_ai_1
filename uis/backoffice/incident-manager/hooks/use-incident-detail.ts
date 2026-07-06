"use client";

import { useEffect, useState } from "react";

import { getIncident } from "@backoffice/incident-manager/lib/incidents-api";
import type { Incident } from "@backoffice/incident-manager/types/incidents";

export const useIncidentDetail = (incidentId: number) => {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getIncident(incidentId)
      .then(setIncident)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load incident"))
      .finally(() => setLoading(false));
  }, [incidentId]);

  return { incident, loading, error };
};
