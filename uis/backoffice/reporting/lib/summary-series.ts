import { formatNumber, formatRate } from "@backoffice/reporting/lib/kpi-definitions";
import {
  rollupAuth,
  rollupConsumption,
  rollupStock,
  rollupWaste,
} from "@backoffice/reporting/lib/monthly-rollup";
import { filterByMonth, lastTwelveMonthKeys } from "@backoffice/reporting/lib/report-window";
import type { ReportMetrics } from "@backoffice/reporting/types/reporting";

/** YYYY-MM → mm/dd/yy (first day of month). */
export const monthToUsDate = (month: string): string => {
  const [year, mm] = month.split("-");
  return `${mm}/01/${year.slice(2)}`;
};

const fill = (values: Map<string, number>, asPercent = false): number[] =>
  lastTwelveMonthKeys().map((month) => {
    const raw = values.get(month) ?? 0;
    return asPercent ? raw * 100 : raw;
  });

const sumByMonth = (rows: Array<{ month: string; count: number }>): Map<string, number> => {
  const map = new Map<string, number>();
  for (const row of rows) map.set(row.month, (map.get(row.month) ?? 0) + row.count);
  return map;
};

export type SummaryKpiCard = {
  id: string;
  title: string;
  headline: string;
  detail: string;
};

export type SummarySeries = {
  id: string;
  label: string;
  color: string;
  values: number[];
  scale: "count" | "percent";
};

export type SummaryChartData = {
  dates: string[];
  series: SummarySeries[];
};

export type SummaryView = {
  cards: SummaryKpiCard[];
  consumptionChart: SummaryChartData;
  ratesChart: SummaryChartData;
};

export const buildSummaryView = (
  metrics: ReportMetrics,
  month: string | null = null,
): SummaryView => {
  const scoped: ReportMetrics = month
    ? {
        consumption_volume_per_day: filterByMonth(
          metrics.consumption_volume_per_day ?? [],
          month,
        ),
        waste_rate_per_day: filterByMonth(metrics.waste_rate_per_day ?? [], month),
        insufficient_stock_failures_per_day: filterByMonth(
          metrics.insufficient_stock_failures_per_day ?? [],
          month,
        ),
        auth_failure_rate: filterByMonth(metrics.auth_failure_rate ?? [], month),
      }
    : metrics;

  const consumption = rollupConsumption(scoped.consumption_volume_per_day ?? []);
  const waste = rollupWaste(scoped.waste_rate_per_day ?? []);
  const stock = rollupStock(scoped.insufficient_stock_failures_per_day ?? []);
  const auth = rollupAuth(scoped.auth_failure_rate ?? []);

  const consumptionTotal = consumption.reduce((sum, row) => sum + row.count, 0);
  const wasteByMonth = new Map<string, { waste: number; total: number }>();
  for (const row of waste) {
    const cur = wasteByMonth.get(row.month) ?? { waste: 0, total: 0 };
    cur.waste += row.waste;
    cur.total += row.total;
    wasteByMonth.set(row.month, cur);
  }
  const wasteMap = new Map(
    [...wasteByMonth.entries()].map(([month, v]) => [
      month,
      v.total === 0 ? 0 : v.waste / v.total,
    ]),
  );
  const wasteNum = [...wasteByMonth.values()].reduce((sum, row) => sum + row.waste, 0);
  const wasteDen = [...wasteByMonth.values()].reduce((sum, row) => sum + row.total, 0);

  const stockMap = new Map<string, { count: number; attempts: number }>();
  for (const row of stock) {
    const cur = stockMap.get(row.month) ?? { count: 0, attempts: 0 };
    cur.count += row.count;
    cur.attempts += row.attempts;
    stockMap.set(row.month, cur);
  }
  const stockRate = new Map(
    [...stockMap.entries()].map(([month, v]) => [
      month,
      v.attempts === 0 ? 0 : v.count / v.attempts,
    ]),
  );
  const stockCount = [...stockMap.values()].reduce((s, v) => s + v.count, 0);
  const stockAttempts = [...stockMap.values()].reduce((s, v) => s + v.attempts, 0);
  const authMap = new Map(auth.map((row) => [row.month, row.failure_rate] as const));
  const authFailed = auth.reduce((sum, row) => sum + row.failed, 0);
  const authSucceeded = auth.reduce((sum, row) => sum + row.succeeded, 0);

  const months = lastTwelveMonthKeys();
  return {
    cards: [
      {
        id: "consumption",
        title: "Consumption volume",
        headline: formatNumber(consumptionTotal),
        detail: "Total outbound · 12 months",
      },
      {
        id: "waste",
        title: "Waste rate",
        headline: formatRate(wasteDen === 0 ? 0 : wasteNum / wasteDen),
        detail: "Expiry / total · recomputed",
      },
      {
        id: "stock",
        title: "Stock failures",
        headline: formatRate(stockAttempts === 0 ? 0 : stockCount / stockAttempts),
        detail: `${stockCount} / ${stockAttempts} attempts`,
      },
      {
        id: "auth",
        title: "Auth failure rate",
        headline: formatRate(
          authFailed + authSucceeded === 0 ? 0 : authFailed / (authFailed + authSucceeded),
        ),
        detail: `${authFailed} failed / ${authSucceeded} ok`,
      },
    ],
    consumptionChart: {
      dates: months.map(monthToUsDate),
      series: [
        {
          id: "consumption",
          label: "Consumption",
          color: "#0c4a6e",
          values: fill(sumByMonth(consumption)),
          scale: "count",
        },
      ],
    },
    ratesChart: {
      dates: months.map(monthToUsDate),
      series: [
        {
          id: "waste",
          label: "Waste %",
          color: "#0f766e",
          values: fill(wasteMap, true),
          scale: "percent",
        },
        {
          id: "stock",
          label: "Stock fail %",
          color: "#0284c7",
          values: fill(stockRate, true),
          scale: "percent",
        },
        {
          id: "auth",
          label: "Auth fail %",
          color: "#14b8a6",
          values: fill(authMap, true),
          scale: "percent",
        },
      ],
    },
  };
};
