import { IncidentList } from "@backoffice/incident-manager/components/incident-list";
import { IncidentPageHeader } from "@backoffice/incident-manager/components/incident-page-header";

export default function IncidentListPage() {
  return (
    <>
      <div className="mx-auto max-w-7xl px-4 pt-8 sm:px-6 lg:px-8">
        <IncidentPageHeader title="Incident List" />
      </div>
      <IncidentList />
    </>
  );
}
