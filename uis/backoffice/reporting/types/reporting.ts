export type ReportingTab =
  | "summary"
  | "consumption"
  | "waste"
  | "stock"
  | "auth"
  | "health";

export type ConsumptionDaily = {
  date: string;
  clinic_id: number;
  jurisdiction: string;
  count: number;
};

export type WasteDaily = {
  date: string;
  jurisdiction: string;
  waste_rate: number;
  total: number;
};

export type StockDaily = {
  date: string;
  clinic_id: number;
  jurisdiction: string;
  /** Reporting API may serialize as string; filters coerce with Number(). */
  supply_id: number | string;
  count: number;
  attempts: number;
  rejection_rate: number;
};

export type AuthDaily = {
  date: string;
  failed: number;
  succeeded: number;
  failure_rate: number;
};

export type ReportMetrics = {
  consumption_volume_per_day: ConsumptionDaily[];
  waste_rate_per_day: WasteDaily[];
  insufficient_stock_failures_per_day: StockDaily[];
  auth_failure_rate: AuthDaily[];
};

export type TelemetryReport = {
  period: { from: string; to: string };
  metrics: ReportMetrics;
};

export type PipelineRunLatest = {
  run_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  watermark_from: string | null;
  watermark_to: string | null;
  rows_extracted: number;
  rows_loaded: number;
  rows_quarantined: number;
  error_summary: string | null;
  checkpoint: string | null;
  pipeline_version: string;
};

export type PipelineRunsList = { runs: PipelineRunLatest[] };

export type ConsumptionMonthly = {
  month: string;
  clinic_id: number;
  jurisdiction: string;
  count: number;
};

export type WasteMonthly = {
  month: string;
  jurisdiction: string;
  waste_rate: number;
  total: number;
  waste: number;
};

export type StockMonthly = {
  month: string;
  clinic_id: number;
  jurisdiction: string;
  supply_id: number | string;
  count: number;
  attempts: number;
  rejection_rate: number;
};

export type AuthMonthly = {
  month: string;
  failed: number;
  succeeded: number;
  failure_rate: number;
};

export type ChartPoint = { label: string; value: number };
