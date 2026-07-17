"use client";

import { SummaryKpiCardView } from "@backoffice/reporting/components/summary-kpi-card";
import { SummaryMultiLineChart } from "@backoffice/reporting/components/summary-multi-line-chart";
import { buildSummaryView } from "@backoffice/reporting/lib/summary-series";
import type { ReportMetrics } from "@backoffice/reporting/types/reporting";

type Props = { metrics: ReportMetrics; month: string | null };

export const SummaryPanel = ({ metrics, month }: Props) => {
  const view = buildSummaryView(metrics, month);

  return (
    <section className="space-y-4">
      <p className="text-sm text-slate-600">
        {month
          ? `Filtered overview for ${month}. Open a KPI tab for tables and drill-down.`
          : "Last 12 calendar months overview. Open a KPI tab for tables and daily drill-down."}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {view.cards.map((card) => (
          <SummaryKpiCardView key={card.id} card={card} />
        ))}
      </div>
      <SummaryMultiLineChart
        title="Consumption volume"
        chart={view.consumptionChart}
        mode="count"
      />
      <SummaryMultiLineChart title="Rate KPIs" chart={view.ratesChart} mode="percent" />
    </section>
  );
};
