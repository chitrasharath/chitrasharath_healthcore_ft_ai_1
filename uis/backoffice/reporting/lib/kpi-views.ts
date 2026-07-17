import { formatNumber, formatRate } from "@backoffice/reporting/lib/kpi-definitions";
import {
  defaultLabels,
  type NameLabels,
} from "@backoffice/reporting/lib/display-names";
import {
  rollupAuth,
  rollupConsumption,
  rollupStock,
  rollupWaste,
} from "@backoffice/reporting/lib/monthly-rollup";
import { filterByMonth } from "@backoffice/reporting/lib/report-window";
import type {
  AuthDaily,
  ChartPoint,
  ConsumptionDaily,
  StockDaily,
  WasteDaily,
} from "@backoffice/reporting/types/reporting";

export const buildConsumptionView = (
  rows: ConsumptionDaily[],
  month: string | null,
  labels: NameLabels = defaultLabels(),
) => {
  if (month) {
    const daily = filterByMonth(rows, month);
    const total = daily.reduce((sum, row) => sum + row.count, 0);
    const table = daily.map((row) => ({
      date: row.date,
      clinic: labels.clinicName(row.clinic_id),
      jurisdiction: row.jurisdiction,
      count: row.count,
    }));
    const byDate = new Map<string, number>();
    for (const row of daily) byDate.set(row.date, (byDate.get(row.date) ?? 0) + row.count);
    const chart: ChartPoint[] = [...byDate.entries()].map(([label, value]) => ({ label, value }));
    return {
      headline: formatNumber(total),
      detail: `Daily rows for ${month}`,
      columns: ["date", "clinic", "jurisdiction", "count"],
      table,
      chart,
    };
  }

  const monthly = rollupConsumption(rows);
  const total = monthly.reduce((sum, row) => sum + row.count, 0);
  const byMonth = new Map<string, number>();
  for (const row of monthly) byMonth.set(row.month, (byMonth.get(row.month) ?? 0) + row.count);
  return {
    headline: formatNumber(total),
    detail: "Sum of consumption counts across last 12 months",
    columns: ["month", "clinic", "jurisdiction", "count"],
    table: monthly.map((row) => ({
      month: row.month,
      clinic: labels.clinicName(row.clinic_id),
      jurisdiction: row.jurisdiction,
      count: row.count,
    })),
    chart: [...byMonth.entries()].map(([label, value]) => ({ label, value })),
  };
};

export const buildWasteView = (rows: WasteDaily[], month: string | null) => {
  if (month) {
    const daily = filterByMonth(rows, month);
    let waste = 0;
    let total = 0;
    for (const row of daily) {
      waste += row.waste_rate * row.total;
      total += row.total;
    }
    const rate = total === 0 ? 0 : waste / total;
    return {
      headline: formatRate(rate),
      detail: `Recomputed from ${month} daily rows`,
      columns: ["date", "jurisdiction", "waste_rate", "total"],
      table: daily.map((row) => ({
        date: row.date,
        jurisdiction: row.jurisdiction,
        waste_rate: formatRate(row.waste_rate),
        total: row.total,
      })),
      chart: daily.map((row) => ({
        label: `${row.date} ${row.jurisdiction}`,
        value: row.waste_rate * 100,
      })),
    };
  }

  const monthly = rollupWaste(rows);
  let waste = 0;
  let total = 0;
  for (const row of monthly) {
    waste += row.waste;
    total += row.total;
  }
  const rate = total === 0 ? 0 : waste / total;
  return {
    headline: formatRate(rate),
    detail: "Monthly waste / total (not averaged daily rates)",
    columns: ["month", "jurisdiction", "waste_rate", "total"],
    table: monthly.map((row) => ({
      month: row.month,
      jurisdiction: row.jurisdiction,
      waste_rate: formatRate(row.waste_rate),
      total: row.total,
    })),
    chart: monthly.map((row) => ({
      label: `${row.month} ${row.jurisdiction}`,
      value: row.waste_rate * 100,
    })),
  };
};

export const buildStockView = (
  rows: StockDaily[],
  month: string | null,
  labels: NameLabels = defaultLabels(),
) => {
  if (month) {
    const daily = filterByMonth(rows, month);
    const count = daily.reduce((sum, row) => sum + row.count, 0);
    const attempts = daily.reduce((sum, row) => sum + row.attempts, 0);
    const rate = attempts === 0 ? 0 : count / attempts;
    return {
      headline: formatRate(rate),
      detail: `${count} failures / ${attempts} attempts in ${month}`,
      columns: ["date", "clinic", "jurisdiction", "supply", "count", "attempts", "rejection_rate"],
      table: daily.map((row) => ({
        date: row.date,
        clinic: labels.clinicName(row.clinic_id),
        jurisdiction: row.jurisdiction,
        supply: labels.supplyName(row.supply_id),
        count: row.count,
        attempts: row.attempts,
        rejection_rate: formatRate(row.rejection_rate),
      })),
      // Period-only labels; grain stays in `id` (and the table) so filter dims are not repeated on bars.
      chart: daily.map((row) => ({
        id: `${row.date}|${row.clinic_id}|${row.jurisdiction}|${row.supply_id}`,
        label: row.date,
        value: row.rejection_rate * 100,
      })),
    };
  }

  const monthly = rollupStock(rows);
  const count = monthly.reduce((sum, row) => sum + row.count, 0);
  const attempts = monthly.reduce((sum, row) => sum + row.attempts, 0);
  const rate = attempts === 0 ? 0 : count / attempts;
  return {
    headline: formatRate(rate),
    detail: `${count} failures / ${attempts} attempts (12-month rollup)`,
    columns: ["month", "clinic", "jurisdiction", "supply", "count", "attempts", "rejection_rate"],
    table: monthly.map((row) => ({
      month: row.month,
      clinic: labels.clinicName(row.clinic_id),
      jurisdiction: row.jurisdiction,
      supply: labels.supplyName(row.supply_id),
      count: row.count,
      attempts: row.attempts,
      rejection_rate: formatRate(row.rejection_rate),
    })),
    chart: monthly.map((row) => ({
      id: `${row.month}|${row.clinic_id}|${row.jurisdiction}|${row.supply_id}`,
      label: row.month,
      value: row.rejection_rate * 100,
    })),
  };
};

export const buildAuthView = (rows: AuthDaily[], month: string | null) => {
  if (month) {
    const daily = filterByMonth(rows, month);
    const failed = daily.reduce((sum, row) => sum + row.failed, 0);
    const succeeded = daily.reduce((sum, row) => sum + row.succeeded, 0);
    const rate = failed + succeeded === 0 ? 0 : failed / (failed + succeeded);
    return {
      headline: formatRate(rate),
      detail: `${failed} failed / ${succeeded} succeeded in ${month}`,
      columns: ["date", "failed", "succeeded", "failure_rate"],
      table: daily.map((row) => ({
        date: row.date,
        failed: row.failed,
        succeeded: row.succeeded,
        failure_rate: formatRate(row.failure_rate),
      })),
      chart: daily.map((row) => ({ label: row.date, value: row.failure_rate * 100 })),
    };
  }

  const monthly = rollupAuth(rows);
  const failed = monthly.reduce((sum, row) => sum + row.failed, 0);
  const succeeded = monthly.reduce((sum, row) => sum + row.succeeded, 0);
  const rate = failed + succeeded === 0 ? 0 : failed / (failed + succeeded);
  return {
    headline: formatRate(rate),
    detail: `${failed} failed / ${succeeded} succeeded (12-month rollup)`,
    columns: ["month", "failed", "succeeded", "failure_rate"],
    table: monthly.map((row) => ({
      month: row.month,
      failed: row.failed,
      succeeded: row.succeeded,
      failure_rate: formatRate(row.failure_rate),
    })),
    chart: monthly.map((row) => ({ label: row.month, value: row.failure_rate * 100 })),
  };
};
