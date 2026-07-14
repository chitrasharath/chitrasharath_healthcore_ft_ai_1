import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type {
  PipelineRunLatest,
  TelemetryReport,
} from "@backoffice/reporting/types/reporting";

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

const reportingFetch = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await healthcoreFetch(path, init);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<T>;
};

export const fetchTelemetryReport = (
  startDate: string,
  endDate: string,
): Promise<TelemetryReport> => {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });
  return reportingFetch<TelemetryReport>(`/telemetry/report?${params}`);
};

export const fetchLatestPipelineRun = (): Promise<PipelineRunLatest> =>
  reportingFetch<PipelineRunLatest>("/telemetry/pipelines/runs/latest");

export const triggerPipelineRun = (): Promise<{ message: string; run_id: string }> =>
  reportingFetch("/telemetry/pipelines/runs/trigger", { method: "POST" });
