"use client";

import { IncidentFormFields } from "@backoffice/incident-manager/components/incident-form-fields";
import { StatusBanner } from "@backoffice/incident-manager/components/status-banner";
import { incidentSubmitClass } from "@backoffice/incident-manager/lib/form-styles";
import { useIncidentForm } from "@backoffice/incident-manager/hooks/use-incident-form";

export const IncidentForm = () => {
  const { form, loading, success, error, fieldError, update, submit } = useIncidentForm();

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <form
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {success ? <StatusBanner variant="success" message={success} /> : null}
        {error ? <StatusBanner variant="error" message={error} /> : null}
        <IncidentFormFields form={form} fieldError={fieldError} onChange={update} />
        <button type="submit" disabled={loading} className={incidentSubmitClass}>
          {loading ? "Logging incident…" : "Log Incident"}
        </button>
      </form>
    </main>
  );
};
