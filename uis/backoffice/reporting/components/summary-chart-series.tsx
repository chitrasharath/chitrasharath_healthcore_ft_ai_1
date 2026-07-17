import { pointX, pointY, seriesPath } from "@backoffice/reporting/lib/chart-geometry";
import type { SummarySeries } from "@backoffice/reporting/lib/summary-series";

type Props = {
  series: SummarySeries[];
  datesLen: number;
  yMax: number;
  innerW: number;
  innerH: number;
};

export const SummaryChartSeries = ({ series, datesLen, yMax, innerW, innerH }: Props) => (
  <>
    {series.map((s) => (
      <g key={s.id}>
        <path
          d={seriesPath(s, datesLen, yMax, innerW, innerH)}
          fill="none"
          stroke={s.color}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {s.values.map((value, index) => (
          <circle
            key={`${s.id}-${index}`}
            cx={pointX(index, datesLen, innerW)}
            cy={pointY(value, yMax, innerH)}
            r={3}
            fill={s.color}
          />
        ))}
      </g>
    ))}
  </>
);
