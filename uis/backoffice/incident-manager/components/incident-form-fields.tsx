import {
  BRANCHES,
  CATEGORIES,
  ORIGINS,
} from "@backoffice/incident-manager/lib/constants";
import { incidentInputClass } from "@backoffice/incident-manager/lib/form-styles";
import type { IncidentCreate } from "@backoffice/incident-manager/types/incidents";

type IncidentFormFieldsProps = {
  form: IncidentCreate;
  fieldError: string | null;
  onChange: (patch: Partial<IncidentCreate>) => void;
};

export const IncidentFormFields = ({ form, fieldError, onChange }: IncidentFormFieldsProps) => {
  const branchHighlight = form.origin === "branch";
  return (
    <>
      <label className="block space-y-1">
        <span className="text-sm font-medium text-slate-700">Title</span>
        <input className={incidentInputClass} value={form.title} onChange={(e) => onChange({ title: e.target.value })} required />
        {fieldError?.includes("Title") ? <span className="text-sm text-red-600">{fieldError}</span> : null}
      </label>
      <label className="block space-y-1">
        <span className="text-sm font-medium text-slate-700">Description</span>
        <textarea className={`${incidentInputClass} min-h-[100px]`} value={form.description} onChange={(e) => onChange({ description: e.target.value })} required />
      </label>
      <label className="block space-y-1">
        <span className="text-sm font-medium text-slate-700">Category</span>
        <select className={incidentInputClass} value={form.category} onChange={(e) => onChange({ category: e.target.value })}>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </label>
      <label className="block space-y-1">
        <span className="text-sm font-medium text-slate-700">Origin</span>
        <select className={incidentInputClass} value={form.origin} onChange={(e) => onChange({ origin: e.target.value })}>
          {ORIGINS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
      <label className={`block space-y-1 ${branchHighlight ? "rounded-lg border-l-4 border-teal-500 bg-sky-50 px-3 py-2" : ""}`}>
        <span className="text-sm font-medium text-slate-700">Branch</span>
        <select className={incidentInputClass} value={form.branch} onChange={(e) => onChange({ branch: e.target.value })}>
          {BRANCHES.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
        </select>
      </label>
    </>
  );
};
