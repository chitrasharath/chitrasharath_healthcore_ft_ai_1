import type { IncidentAnalysisResponse } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function analyzeIncidents(file: File): Promise<IncidentAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/v1/incidents/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Unable to analyze incidents file.");
  }

  return response.json() as Promise<IncidentAnalysisResponse>;
}

export async function exportAnalysisResults(): Promise<Blob> {
  const response = await fetch(`${API_URL}/api/v1/incidents/results/export`);

  if (response.status === 404) {
    throw new Error("No analysis available. Upload a CSV first.");
  }

  if (!response.ok) {
    throw new Error("Unable to export analysis results.");
  }

  return response.blob();
}
