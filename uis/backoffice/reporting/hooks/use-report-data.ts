"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchTelemetryReport } from "@backoffice/reporting/lib/reporting-api";
import { reportWindowIso } from "@backoffice/reporting/lib/report-window";
import type { TelemetryReport } from "@backoffice/reporting/types/reporting";

export const useReportData = () => {
  const [report, setReport] = useState<TelemetryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { start, end } = reportWindowIso();
      setReport(await fetchTelemetryReport(start, end));
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { report, loading, error, reload };
};
