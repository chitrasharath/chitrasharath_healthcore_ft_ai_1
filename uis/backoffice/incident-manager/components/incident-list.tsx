"use client";

import { IncidentListFilters } from "@backoffice/incident-manager/components/incident-list-filters";
import { IncidentListTable } from "@backoffice/incident-manager/components/incident-list-table";
import { StatusBanner } from "@backoffice/incident-manager/components/status-banner";
import { useIncidentList } from "@backoffice/incident-manager/hooks/use-incident-list";
import { useIncidentSort } from "@backoffice/incident-manager/hooks/use-incident-sort";

export const IncidentList = () => {
  const { filters, setFilters, incidents, loading, error, statusError, load, changeStatus } =
    useIncidentList();
  const { sortKey, sortDirection, toggleSort, sortedIncidents } = useIncidentSort(incidents);

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <IncidentListFilters filters={filters} onChange={setFilters} />
      {statusError ? <StatusBanner variant="error" message={statusError} /> : null}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {loading ? <p className="text-sm font-medium text-sky-800">Loading incidents…</p> : null}
        {!loading && error ? (
          <div className="space-y-3">
            <StatusBanner variant="error" message={error} />
            <button type="button" onClick={() => void load()} className="rounded-md bg-sky-700 px-4 py-2 text-sm font-bold text-white">
              Retry
            </button>
          </div>
        ) : null}
        {!loading && !error && incidents.length === 0 ? (
          <p className="text-sm text-slate-600">No incidents match the current filters.</p>
        ) : null}
        {!loading && !error && incidents.length > 0 ? (
          <IncidentListTable
            incidents={sortedIncidents}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onSort={toggleSort}
            onStatusChange={(id, s) => void changeStatus(id, s)}
          />
        ) : null}
      </section>
    </main>
  );
};
