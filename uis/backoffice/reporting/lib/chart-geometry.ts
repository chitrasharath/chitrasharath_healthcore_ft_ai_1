import type { SummarySeries } from "@backoffice/reporting/lib/summary-series";

export const CHART_PAD = { top: 20, right: 52, bottom: 40, left: 48 };
export const CHART_W = 720;
export const CHART_H = 260;

export const pointX = (index: number, datesLen: number, innerW: number): number =>
  CHART_PAD.left + (datesLen === 1 ? innerW / 2 : (index / (datesLen - 1)) * innerW);

export const pointY = (value: number, yMax: number, innerH: number): number =>
  CHART_PAD.top + innerH - (value / Math.max(yMax, 0.0001)) * innerH;

export const seriesPath = (
  series: SummarySeries,
  datesLen: number,
  yMax: number,
  innerW: number,
  innerH: number,
): string =>
  series.values
    .map((value, index) => {
      const x = pointX(index, datesLen, innerW);
      const y = pointY(value, yMax, innerH);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

export const axisTicks = (yMax: number, count = 4): number[] =>
  Array.from({ length: count }, (_, i) => (yMax * i) / (count - 1));

export const tickY = (value: number, yMax: number, innerH: number): number =>
  pointY(value, yMax, innerH);

export const scaleMax = (series: SummarySeries[], scale: "count" | "percent"): number => {
  const values = series.filter((s) => s.scale === scale).flatMap((s) => s.values);
  const peak = Math.max(0, ...values);
  if (scale === "percent") return Math.max(peak, 1);
  return Math.max(peak, 1);
};
