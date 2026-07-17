import type { ChartPoint } from "@backoffice/reporting/types/reporting";

type Props = { points: ChartPoint[]; valueSuffix?: string };

export const KpiBarChart = ({ points, valueSuffix = "" }: Props) => {
  if (points.length === 0) {
    return <p className="text-sm text-slate-500">No chart data for this view.</p>;
  }

  const max = Math.max(...points.map((point) => point.value), 0.0001);

  return (
    <ul className="space-y-2" aria-label="KPI chart">
      {points.map((point) => {
        const width = `${Math.max((point.value / max) * 100, 2)}%`;
        return (
          <li
            key={point.id ?? point.label}
            className="grid grid-cols-[minmax(0,12rem)_1fr_4.5rem] items-center gap-2 text-sm"
          >
            <span className="truncate font-medium text-slate-700" title={point.label}>
              {point.label}
            </span>
            <div className="h-3 overflow-hidden rounded bg-slate-100">
              <div className="h-full rounded bg-teal-600" style={{ width }} />
            </div>
            <span className="text-right tabular-nums text-slate-600">
              {point.value.toFixed(point.value < 1 && point.value > 0 ? 3 : 1)}
              {valueSuffix}
            </span>
          </li>
        );
      })}
    </ul>
  );
};
