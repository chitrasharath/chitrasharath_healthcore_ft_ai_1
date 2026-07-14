"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { KpiTabPanel } from "@backoffice/reporting/components/kpi-tab-panel";
import { PipelineHealthPanel } from "@backoffice/reporting/components/pipeline-health-panel";
import { ReportingFilterBar } from "@backoffice/reporting/components/reporting-filter-bar";
import { ReportingHero } from "@backoffice/reporting/components/reporting-hero";
import { ReportingTabs } from "@backoffice/reporting/components/reporting-tabs";
import { StatusBanner } from "@backoffice/reporting/components/status-banner";
import { SummaryPanel } from "@backoffice/reporting/components/summary-panel";
import { useReportData } from "@backoffice/reporting/hooks/use-report-data";
import { useSupplyNames } from "@backoffice/reporting/hooks/use-supply-names";
import { parseTab, type KpiTab } from "@backoffice/reporting/lib/kpi-definitions";
import {
  applyReportFilters,
  parseReportFilters,
  uniqueClinics,
  uniqueJurisdictions,
  uniqueSupplies,
} from "@backoffice/reporting/lib/report-filters";

const isKpiTab = (tab: string): tab is KpiTab =>
  tab === "consumption" || tab === "waste" || tab === "stock" || tab === "auth";

const ReportingBody = () => {
  const searchParams = useSearchParams();
  const tab = parseTab(searchParams.get("tab"));
  const filters = parseReportFilters(searchParams);
  const { report, loading, error } = useReportData();
  const supplyNames = useSupplyNames();
  const showFilters = tab === "consumption" || tab === "waste" || tab === "stock";
  const filterHint =
    tab === "waste"
      ? "Waste rate is rolled up by jurisdiction (not clinic). Use month and jurisdiction filters."
      : tab === "stock"
        ? "Stock failures support month, jurisdiction, clinic, and supply filters."
        : "Consumption supports month, jurisdiction, and clinic filters.";
  const filtered = report
    ? showFilters
      ? applyReportFilters(report.metrics, filters)
      : report.metrics
    : null;

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <ReportingHero />
      <ReportingTabs active={tab} />
      {report && showFilters ? (
        <ReportingFilterBar
          filters={filters}
          jurisdictions={uniqueJurisdictions(report.metrics)}
          clinics={uniqueClinics(report.metrics, filters.jurisdiction)}
          supplies={uniqueSupplies(report.metrics, filters.jurisdiction)}
          supplyNames={supplyNames}
          showClinic={tab !== "waste"}
          showSupply={tab === "stock"}
          hint={filterHint}
        />
      ) : null}
      {tab !== "health" && loading ? <p className="text-sm text-slate-500">Loading report…</p> : null}
      {tab !== "health" && error ? <StatusBanner message={error} /> : null}
      {tab === "health" ? <PipelineHealthPanel /> : null}
      {tab === "summary" && filtered ? <SummaryPanel metrics={filtered} month={null} /> : null}
      {isKpiTab(tab) && filtered ? (
        <KpiTabPanel
          tab={tab}
          metrics={filtered}
          month={showFilters ? filters.month : null}
          supplyNames={supplyNames}
        />
      ) : null}
    </main>
  );
};

export const ReportingDashboard = () => (
  <Suspense fallback={<p className="p-8 text-sm text-slate-500">Loading reporting…</p>}>
    <ReportingBody />
  </Suspense>
);
