import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type { IncidentAnalysisResponse } from "@backoffice/incident-analyzer/lib/types";

const parseError = async (response: Response): Promise<string> => {
  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  return payload?.detail ?? "Unable to analyze incidents file.";
};

export async function analyzeIncidents(file: File): Promise<IncidentAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await healthcoreFetch("/incidents/analyze", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json() as Promise<IncidentAnalysisResponse>;
}

export async function exportAnalysisResults(): Promise<Blob> {
  const response = await healthcoreFetch("/incidents/results/export");

  if (response.status === 404) {
    throw new Error("No analysis available. Upload a CSV first.");
  }

  if (!response.ok) {
    throw new Error("Unable to export analysis results.");
  }

  return response.blob();
}
