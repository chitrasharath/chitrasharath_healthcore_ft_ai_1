"use client";

import { useEffect, useState } from "react";

import { getIncidentSummary } from "@backoffice/incident-manager/lib/incidents-api";
import type { IncidentSummary } from "@backoffice/incident-manager/types/incidents";
import { StatusBanner } from "@backoffice/incident-manager/components/status-banner";
import { SummarySection } from "@backoffice/incident-manager/components/summary-section";
import {
  BRANCHES,
  CATEGORIES,
  ORIGINS,
  STATUSES,
} from "@backoffice/incident-manager/lib/constants";

export const IncidentSummaryView = () => {
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getIncidentSummary()
      .then(setSummary)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load summary"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      {loading ? <p className="text-sm font-medium text-sky-800">Loading summary…</p> : null}
      {error ? <StatusBanner variant="error" message={error} /> : null}
      {summary ? (
        <div className="grid gap-5 lg:grid-cols-2">
          <SummarySection title="By Status" data={summary.by_status} labels={STATUSES} />
          <SummarySection title="By Category" data={summary.by_category} labels={CATEGORIES} />
          <SummarySection title="By Origin" data={summary.by_origin} labels={ORIGINS} />
          <SummarySection title="By Branch" data={summary.by_branch} labels={BRANCHES} dynamicOnly />
        </div>
      ) : null}
    </main>
  );
};
