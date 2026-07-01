"use client";

import { IncidentFormFields } from "@backoffice/incident-manager/components/incident-form-fields";
import { StatusBanner } from "@backoffice/incident-manager/components/status-banner";
import { incidentSubmitClass } from "@backoffice/incident-manager/lib/form-styles";
import { useIncidentEdit } from "@backoffice/incident-manager/hooks/use-incident-edit";

type IncidentEditFormProps = {
  incidentId: number;
};

export const IncidentEditForm = ({ incidentId }: IncidentEditFormProps) => {
  const { form, loading, saving, error, success, fieldError, update, submit } = useIncidentEdit(incidentId);

  if (loading) return <p className="text-sm font-medium text-sky-800">Loading incident…</p>;
  if (!form) return error ? <StatusBanner variant="error" message={error} /> : null;

  return (
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
      <button type="submit" disabled={saving} className={incidentSubmitClass}>
        {saving ? "Saving changes…" : "Save changes"}
      </button>
    </form>
  );
};
