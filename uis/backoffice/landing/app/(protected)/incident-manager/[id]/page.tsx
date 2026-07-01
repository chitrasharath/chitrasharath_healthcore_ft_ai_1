import { Suspense } from "react";

import { IncidentDetail } from "@backoffice/incident-manager/components/incident-detail";
import { IncidentPageHeader } from "@backoffice/incident-manager/components/incident-page-header";

type IncidentDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function IncidentDetailPage({ params }: IncidentDetailPageProps) {
  const { id } = await params;
  const incidentId = Number(id);
  if (!Number.isInteger(incidentId) || incidentId <= 0) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8">
        <p className="text-sm text-red-600">Invalid incident ID.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <IncidentPageHeader title="Incident details" backHref="/incident-manager/list" backLabel="← Back to Incident List" />
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <Suspense fallback={<p className="text-sm font-medium text-sky-800">Loading incident…</p>}>
          <IncidentDetail incidentId={incidentId} />
        </Suspense>
      </section>
    </main>
  );
}
