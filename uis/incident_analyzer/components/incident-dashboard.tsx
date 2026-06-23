"use client";

import { AnalysisSummary } from "@backoffice/incident-analyzer/components/analysis-summary";
import { BreakdownSection } from "@backoffice/incident-analyzer/components/breakdown-section";
import { CsvUpload } from "@backoffice/incident-analyzer/components/csv-upload";
import { ExportButton } from "@backoffice/incident-analyzer/components/export-button";
import { IncidentHeader } from "@backoffice/incident-analyzer/components/layout/incident-header";
import { SatisfactionSection } from "@backoffice/incident-analyzer/components/satisfaction-section";
import { useIncidentAnalysis } from "@backoffice/incident-analyzer/hooks/use-incident-analysis";

export const IncidentDashboard = () => {
  const { loading, exporting, error, result, upload, exportResults } = useIncidentAnalysis();

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <IncidentHeader sourceFilename={result?.source_filename} analyzedAt={result?.analyzed_at} />
      <CsvUpload disabled={loading} onFileSelected={upload} />
      {loading ? <p className="text-sm font-medium text-sky-800">Analyzing…</p> : null}
      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      {result ? (
        <>
          <AnalysisSummary totals={result.totals} invalidBreakdown={result.invalid_breakdown} />
          <div className="grid gap-5 lg:grid-cols-2">
            <BreakdownSection title="Breakdown by category (valid records)" items={result.by_category} highlightLabel="ACCESSIBILITY" />
            <BreakdownSection title="Breakdown by status (valid records)" items={result.by_status} />
            <BreakdownSection title="Breakdown by country (valid records)" items={result.by_country} />
            <SatisfactionSection satisfaction={result.satisfaction} />
          </div>
          <ExportButton disabled={!result} exporting={exporting} onExport={exportResults} />
        </>
      ) : null}
    </main>
  );
};
