"use client";

import { KpiBarChart } from "@backoffice/reporting/components/kpi-bar-chart";
import { KpiDefinition } from "@backoffice/reporting/components/kpi-definition";
import { KpiHeadline } from "@backoffice/reporting/components/kpi-headline";
import { KpiTable } from "@backoffice/reporting/components/kpi-table";
import { KPI_DEFINITIONS, type KpiTab } from "@backoffice/reporting/lib/kpi-definitions";
import { defaultLabels } from "@backoffice/reporting/lib/display-names";
import {
  buildAuthView,
  buildConsumptionView,
  buildStockView,
  buildWasteView,
} from "@backoffice/reporting/lib/kpi-views";
import type { ReportMetrics } from "@backoffice/reporting/types/reporting";

type Props = {
  tab: KpiTab;
  metrics: ReportMetrics;
  month: string | null;
  supplyNames: Record<number, string>;
};

export const KpiTabPanel = ({ tab, metrics, month, supplyNames }: Props) => {
  const labels = defaultLabels(supplyNames);
  const view =
    tab === "consumption"
      ? buildConsumptionView(metrics.consumption_volume_per_day, month, labels)
      : tab === "waste"
        ? buildWasteView(metrics.waste_rate_per_day, month)
        : tab === "stock"
          ? buildStockView(metrics.insufficient_stock_failures_per_day, month, labels)
          : buildAuthView(metrics.auth_failure_rate, month);
  const isRate = tab !== "consumption";

  return (
    <section className="space-y-4">
      <KpiDefinition text={KPI_DEFINITIONS[tab]} />
      <KpiHeadline
        title={month ? `Daily · ${month}` : "Last 12 months"}
        value={view.headline}
        detail={view.detail}
      />
      <KpiBarChart points={view.chart} valueSuffix={isRate ? "%" : ""} />
      <KpiTable columns={view.columns} rows={view.table} />
    </section>
  );
};
