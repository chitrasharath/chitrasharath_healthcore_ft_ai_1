"use client";

import { SummaryChartAxes, SummaryChartDates } from "@backoffice/reporting/components/summary-chart-axes";
import { SummaryChartSeries } from "@backoffice/reporting/components/summary-chart-series";
import {
  CHART_H,
  CHART_PAD,
  CHART_W,
  pointX,
  scaleMax,
} from "@backoffice/reporting/lib/chart-geometry";
import type { SummaryChartData } from "@backoffice/reporting/lib/summary-series";

type Props = {
  title: string;
  chart: SummaryChartData | undefined;
  mode: "count" | "percent";
};

export const SummaryMultiLineChart = ({ title, chart, mode }: Props) => {
  if (!chart || chart.dates.length === 0 || chart.series.length === 0) {
    return <p className="text-sm text-slate-500">No chart data for this view.</p>;
  }

  const { dates, series } = chart;
  const innerW = CHART_W - CHART_PAD.left - CHART_PAD.right;
  const innerH = CHART_H - CHART_PAD.top - CHART_PAD.bottom;
  const yMax = scaleMax(series, mode);
  const rightX = CHART_W - CHART_PAD.right;

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
      <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="h-auto w-full" role="img" aria-label={title}>
        <SummaryChartAxes yMax={yMax} innerH={innerH} rightX={rightX} mode={mode} />
        <SummaryChartSeries
          series={series}
          datesLen={dates.length}
          yMax={yMax}
          innerW={innerW}
          innerH={innerH}
        />
        <SummaryChartDates dates={dates} innerW={innerW} pointX={pointX} />
      </svg>
      <ul className="flex flex-wrap gap-4 text-xs text-slate-700">
        {series.map((s) => (
          <li key={s.id} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            {s.label}
          </li>
        ))}
      </ul>
      <p className="text-xs text-slate-500">
        {mode === "count" ? "Y-axis: event count." : "Y-axis: rate (%)."} Dates are month starts
        (mm/dd/yy).
      </p>
    </div>
  );
};
