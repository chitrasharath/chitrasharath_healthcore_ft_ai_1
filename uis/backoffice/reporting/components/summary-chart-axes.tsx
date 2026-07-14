import { axisTicks, CHART_H, CHART_PAD, tickY } from "@backoffice/reporting/lib/chart-geometry";

type Props = {
  yMax: number;
  innerH: number;
  rightX: number;
  mode: "count" | "percent";
};

export const SummaryChartAxes = ({ yMax, innerH, rightX, mode }: Props) => (
  <>
    <line
      x1={CHART_PAD.left}
      y1={CHART_PAD.top}
      x2={CHART_PAD.left}
      y2={CHART_PAD.top + innerH}
      stroke={mode === "count" ? "#0c4a6e" : "#0f766e"}
    />
    <line
      x1={CHART_PAD.left}
      y1={CHART_PAD.top + innerH}
      x2={rightX}
      y2={CHART_PAD.top + innerH}
      stroke="#e0f2fe"
    />
    {axisTicks(yMax).map((value) => (
      <text
        key={`Y${value}`}
        x={CHART_PAD.left - 6}
        y={tickY(value, yMax, innerH) + 3}
        textAnchor="end"
        className={mode === "count" ? "fill-sky-900 text-[9px]" : "fill-teal-700 text-[9px]"}
      >
        {mode === "percent" ? `${value.toFixed(0)}%` : Math.round(value)}
      </text>
    ))}
  </>
);

type DateProps = {
  dates: string[];
  innerW: number;
  pointX: (i: number, n: number, w: number) => number;
};

export const SummaryChartDates = ({ dates, innerW, pointX }: DateProps) => (
  <>
    {dates.map((date, index) => {
      if (index % 2 !== 0 && index !== dates.length - 1) return null;
      return (
        <text
          key={date}
          x={pointX(index, dates.length, innerW)}
          y={CHART_H - 12}
          textAnchor="middle"
          className="fill-slate-500 text-[9px]"
        >
          {date}
        </text>
      );
    })}
  </>
);
