"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchLatestPipelineRun,
  fetchRecentPipelineRuns,
  triggerPipelineRun,
} from "@backoffice/reporting/lib/reporting-api";
import type { PipelineRunLatest } from "@backoffice/reporting/types/reporting";

export const usePipelineHealth = () => {
  const [run, setRun] = useState<PipelineRunLatest | null>(null);
  const [recent, setRecent] = useState<PipelineRunLatest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [latest, list] = await Promise.all([
        fetchLatestPipelineRun(),
        fetchRecentPipelineRuns(14),
      ]);
      setRun(latest);
      setRecent(list.runs);
    } catch (err) {
      setRun(null);
      setRecent([]);
      setError(err instanceof Error ? err.message : "Failed to load pipeline health");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const trigger = useCallback(async () => {
    setTriggering(true);
    setMessage(null);
    try {
      const result = await triggerPipelineRun();
      setMessage(`${result.message} (${result.run_id})`);
      await reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Trigger failed");
    } finally {
      setTriggering(false);
    }
  }, [reload]);

  return { run, recent, loading, error, triggering, message, trigger, reload };
};
