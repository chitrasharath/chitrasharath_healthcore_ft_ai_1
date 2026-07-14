"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchLatestPipelineRun,
  triggerPipelineRun,
} from "@backoffice/reporting/lib/reporting-api";
import type { PipelineRunLatest } from "@backoffice/reporting/types/reporting";

export const usePipelineHealth = () => {
  const [run, setRun] = useState<PipelineRunLatest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRun(await fetchLatestPipelineRun());
    } catch (err) {
      setRun(null);
      setError(err instanceof Error ? err.message : "Failed to load latest run");
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

  return { run, loading, error, triggering, message, trigger, reload };
};
