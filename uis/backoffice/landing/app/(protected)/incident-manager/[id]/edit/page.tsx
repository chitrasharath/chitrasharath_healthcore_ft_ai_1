import { IncidentEditForm } from "@backoffice/incident-manager/components/incident-edit-form";
import { IncidentPageHeader } from "@backoffice/incident-manager/components/incident-page-header";

type IncidentEditPageProps = {
  params: Promise<{ id: string }>;
};

export default async function IncidentEditPage({ params }: IncidentEditPageProps) {
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
      <IncidentPageHeader
        title="Edit incident"
        backHref={`/incident-manager/${incidentId}`}
        backLabel="← Back to incident details"
      />
      <IncidentEditForm incidentId={incidentId} />
    </main>
  );
}
