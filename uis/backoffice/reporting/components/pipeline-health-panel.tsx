"use client";

import { StatusBanner } from "@backoffice/reporting/components/status-banner";
import { usePipelineHealth } from "@backoffice/reporting/hooks/use-pipeline-health";

const Field = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
    <dd className="mt-1 break-all text-sm text-slate-900">{value}</dd>
  </div>
);

export const PipelineHealthPanel = () => {
  const { run, loading, error, triggering, message, trigger } = usePipelineHealth();

  return (
    <section className="space-y-4">
      <p className="text-sm text-slate-600">
        Latest materialized ETL run status. Use Run pipeline for an on-demand refresh; nightly
        cron uses the CLI only.
      </p>
      {loading ? <p className="text-sm text-slate-500">Loading latest run…</p> : null}
      {error ? <StatusBanner message={error} /> : null}
      {message ? <StatusBanner message={message} tone="info" /> : null}
      {run ? (
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Status" value={run.status} />
          <Field label="Run ID" value={run.run_id} />
          <Field label="Checkpoint" value={run.checkpoint ?? "—"} />
          <Field label="Started" value={run.started_at ?? "—"} />
          <Field label="Finished" value={run.finished_at ?? "—"} />
          <Field label="Version" value={run.pipeline_version} />
          <Field label="Watermark from" value={run.watermark_from ?? "—"} />
          <Field label="Watermark to" value={run.watermark_to ?? "—"} />
          <Field label="Rows extracted" value={String(run.rows_extracted)} />
          <Field label="Rows loaded" value={String(run.rows_loaded)} />
          <Field label="Rows quarantined" value={String(run.rows_quarantined)} />
          <Field label="Error summary" value={run.error_summary ?? "—"} />
        </dl>
      ) : null}
      <button
        type="button"
        onClick={() => void trigger()}
        disabled={triggering}
        className="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-60"
      >
        {triggering ? "Submitting…" : "Run pipeline"}
      </button>
    </section>
  );
};
