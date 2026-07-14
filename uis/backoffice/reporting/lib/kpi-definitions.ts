import type { ReportingTab } from "@backoffice/reporting/types/reporting";

export const TAB_LABELS: Record<ReportingTab, string> = {
  summary: "Summary",
  consumption: "Consumption volume",
  waste: "Waste rate",
  stock: "Stock failures",
  auth: "Auth failure rate",
  health: "Pipeline health",
};

export type KpiTab = Exclude<ReportingTab, "summary" | "health">;

export const KPI_DEFINITIONS: Record<KpiTab, string> = {
  consumption:
    "Count of successful outbound consumptions per clinic per day, segmented by jurisdiction (us / uk).",
  waste:
    "Share of outbound events marked expiry_waste versus all outbound consumptions, per jurisdiction per day.",
  stock:
    "Count and rate of outbound orders rejected for insufficient stock, per supply, clinic, and jurisdiction per day.",
  auth:
    "Daily login failure rate from user_login_succeeded versus user_login_failed events (no jurisdiction segment).",
};

export const parseTab = (raw: string | null): ReportingTab => {
  if (
    raw === "summary" ||
    raw === "consumption" ||
    raw === "waste" ||
    raw === "stock" ||
    raw === "auth" ||
    raw === "health"
  ) {
    return raw;
  }
  return "summary";
};

export const formatRate = (value: number): string => `${(value * 100).toFixed(1)}%`;

export const formatNumber = (value: number): string =>
  Number.isInteger(value) ? String(value) : value.toFixed(2);
