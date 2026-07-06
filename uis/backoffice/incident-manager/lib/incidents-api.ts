import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type {
  Incident,
  IncidentCreate,
  IncidentFilters,
  IncidentSummary,
} from "@backoffice/incident-manager/types/incidents";

const parseError = async (response: Response): Promise<string> => {
  const payload = (await response.json().catch(() => null)) as
    | { detail?: string | Array<{ msg?: string }> }
    | null;
  if (payload?.detail) {
    if (typeof payload.detail === "string") return payload.detail;
    return payload.detail.map((item) => item.msg ?? "Validation error").join("; ");
  }
  return response.statusText || "Request failed";
};

const incidentFetch = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await healthcoreFetch(path, init);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<T>;
};

const buildQuery = (filters?: IncidentFilters): string => {
  if (!filters) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
};

export const createIncident = (body: IncidentCreate): Promise<Incident> =>
  incidentFetch<Incident>("/incidents", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const listIncidents = (filters?: IncidentFilters): Promise<Incident[]> =>
  incidentFetch<Incident[]>(`/incidents${buildQuery(filters)}`);

export const getIncident = (id: number): Promise<Incident> =>
  incidentFetch<Incident>(`/incidents/${id}`);

export const updateIncidentStatus = (id: number, status: string): Promise<Incident> =>
  incidentFetch<Incident>(`/incidents/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

export const updateIncident = (id: number, body: IncidentCreate): Promise<Incident> =>
  incidentFetch<Incident>(`/incidents/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const getIncidentSummary = (): Promise<IncidentSummary> =>
  incidentFetch<IncidentSummary>("/incidents/summary");
