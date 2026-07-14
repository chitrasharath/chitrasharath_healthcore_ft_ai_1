import { clinicJurisdiction } from "@backoffice/inventory/lib/constants";
import type {
  ConsumptionDaily,
  ReportMetrics,
  StockDaily,
  WasteDaily,
} from "@backoffice/reporting/types/reporting";

export type ReportFilters = {
  month: string | null;
  jurisdiction: string | null;
  clinicId: number | null;
  supplyId: number | null;
};

export const parseReportFilters = (params: URLSearchParams): ReportFilters => {
  const clinicRaw = params.get("clinic");
  const supplyRaw = params.get("supply");
  const clinicId = clinicRaw && !Number.isNaN(Number(clinicRaw)) ? Number(clinicRaw) : null;
  const supplyId = supplyRaw && !Number.isNaN(Number(supplyRaw)) ? Number(supplyRaw) : null;
  return {
    month: params.get("month"),
    jurisdiction: params.get("jurisdiction"),
    clinicId,
    supplyId,
  };
};

const matchesTagJurisdiction = (value: string, filter: string | null): boolean =>
  !filter || value === filter;

const matchesClinic = (value: number, filter: number | null): boolean =>
  filter === null || value === filter;

/** API/reporting rows may encode supply_id as string; compare numerically. */
const asSupplyId = (value: number | string): number => Number(value);

const matchesSupply = (value: number | string, filter: number | null): boolean =>
  filter === null || asSupplyId(value) === filter;

/** Clinic catalog location wins over supply-derived telemetry jurisdiction. */
const clinicFitsJurisdiction = (clinicId: number, filter: string | null): boolean => {
  if (!filter) return true;
  const location = clinicJurisdiction(clinicId);
  if (location === null) return true;
  return location === filter;
};

/** Dimensional filters only — month grain stays in KPI view builders. */
export const applyReportFilters = (
  metrics: ReportMetrics,
  filters: ReportFilters,
): ReportMetrics => ({
  consumption_volume_per_day: (metrics.consumption_volume_per_day ?? []).filter(
    (row: ConsumptionDaily) =>
      clinicFitsJurisdiction(row.clinic_id, filters.jurisdiction) &&
      matchesClinic(row.clinic_id, filters.clinicId),
  ),
  waste_rate_per_day: (metrics.waste_rate_per_day ?? []).filter((row: WasteDaily) =>
    matchesTagJurisdiction(row.jurisdiction, filters.jurisdiction),
  ),
  insufficient_stock_failures_per_day: (metrics.insufficient_stock_failures_per_day ?? []).filter(
    (row: StockDaily) =>
      clinicFitsJurisdiction(row.clinic_id, filters.jurisdiction) &&
      matchesClinic(row.clinic_id, filters.clinicId) &&
      matchesSupply(row.supply_id, filters.supplyId),
  ),
  auth_failure_rate: metrics.auth_failure_rate ?? [],
});

export const uniqueJurisdictions = (metrics: ReportMetrics): string[] => {
  const set = new Set<string>();
  for (const row of metrics.consumption_volume_per_day) set.add(row.jurisdiction);
  for (const row of metrics.waste_rate_per_day) set.add(row.jurisdiction);
  for (const row of metrics.insufficient_stock_failures_per_day) set.add(row.jurisdiction);
  return [...set].sort();
};

export const uniqueClinics = (
  metrics: ReportMetrics,
  jurisdiction: string | null = null,
): number[] => {
  const set = new Set<number>();
  for (const row of metrics.consumption_volume_per_day) {
    if (clinicFitsJurisdiction(row.clinic_id, jurisdiction)) set.add(row.clinic_id);
  }
  for (const row of metrics.insufficient_stock_failures_per_day) {
    if (clinicFitsJurisdiction(row.clinic_id, jurisdiction)) set.add(row.clinic_id);
  }
  return [...set].sort((a, b) => a - b);
};

export const uniqueSupplies = (
  metrics: ReportMetrics,
  jurisdiction: string | null = null,
): number[] => {
  const set = new Set<number>();
  for (const row of metrics.insufficient_stock_failures_per_day) {
    if (
      clinicFitsJurisdiction(row.clinic_id, jurisdiction) &&
      matchesTagJurisdiction(row.jurisdiction, jurisdiction)
    ) {
      set.add(asSupplyId(row.supply_id));
    }
  }
  return [...set].sort((a, b) => a - b);
};
