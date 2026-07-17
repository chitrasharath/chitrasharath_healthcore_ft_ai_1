import { monthKey } from "@backoffice/reporting/lib/report-window";
import type {
  AuthDaily,
  AuthMonthly,
  ConsumptionDaily,
  ConsumptionMonthly,
  StockDaily,
  StockMonthly,
  WasteDaily,
  WasteMonthly,
} from "@backoffice/reporting/types/reporting";

const rate = (num: number, den: number): number => (den === 0 ? 0 : num / den);

export const rollupConsumption = (rows: ConsumptionDaily[]): ConsumptionMonthly[] => {
  const map = new Map<string, ConsumptionMonthly>();
  for (const row of rows) {
    const month = monthKey(row.date);
    const key = `${month}|${row.clinic_id}|${row.jurisdiction}`;
    const existing = map.get(key);
    if (existing) existing.count += row.count;
    else {
      map.set(key, {
        month,
        clinic_id: row.clinic_id,
        jurisdiction: row.jurisdiction,
        count: row.count,
      });
    }
  }
  return [...map.values()].sort((a, b) => a.month.localeCompare(b.month));
};

export const rollupWaste = (rows: WasteDaily[]): WasteMonthly[] => {
  const map = new Map<string, { month: string; jurisdiction: string; waste: number; total: number }>();
  for (const row of rows) {
    const month = monthKey(row.date);
    const key = `${month}|${row.jurisdiction}`;
    const waste = row.waste_rate * row.total;
    const existing = map.get(key);
    if (existing) {
      existing.waste += waste;
      existing.total += row.total;
    } else map.set(key, { month, jurisdiction: row.jurisdiction, waste, total: row.total });
  }
  return [...map.values()]
    .map((r) => ({
      month: r.month,
      jurisdiction: r.jurisdiction,
      waste: r.waste,
      total: r.total,
      waste_rate: rate(r.waste, r.total),
    }))
    .sort((a, b) => a.month.localeCompare(b.month));
};

export const rollupStock = (rows: StockDaily[]): StockMonthly[] => {
  const map = new Map<string, StockMonthly>();
  for (const row of rows) {
    const month = monthKey(row.date);
    const key = `${month}|${row.clinic_id}|${row.jurisdiction}|${row.supply_id}`;
    const existing = map.get(key);
    if (existing) {
      existing.count += row.count;
      existing.attempts += row.attempts;
      existing.rejection_rate = rate(existing.count, existing.attempts);
    } else {
      map.set(key, {
        month,
        clinic_id: row.clinic_id,
        jurisdiction: row.jurisdiction,
        supply_id: row.supply_id,
        count: row.count,
        attempts: row.attempts,
        rejection_rate: rate(row.count, row.attempts),
      });
    }
  }
  return [...map.values()].sort((a, b) => a.month.localeCompare(b.month));
};

export const rollupAuth = (rows: AuthDaily[]): AuthMonthly[] => {
  const map = new Map<string, AuthMonthly>();
  for (const row of rows) {
    const month = monthKey(row.date);
    const existing = map.get(month);
    if (existing) {
      existing.failed += row.failed;
      existing.succeeded += row.succeeded;
      existing.failure_rate = rate(existing.failed, existing.failed + existing.succeeded);
    } else {
      map.set(month, {
        month,
        failed: row.failed,
        succeeded: row.succeeded,
        failure_rate: rate(row.failed, row.failed + row.succeeded),
      });
    }
  }
  return [...map.values()].sort((a, b) => a.month.localeCompare(b.month));
};
