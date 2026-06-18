import type { SupplierDetailsInput } from "@/lib/types";

type SupplierOptionalFieldsProps = {
  form: SupplierDetailsInput;
  onChange: (form: SupplierDetailsInput) => void;
};

export const SupplierOptionalFields = ({ form, onChange }: SupplierOptionalFieldsProps) => (
  <>
    <label className="block text-sm font-medium text-slate-700">
      Compliance agreement
      <select
        value={form.compliance_agreement ?? ""}
        onChange={(e) => onChange({ ...form, compliance_agreement: e.target.value || null })}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      >
        <option value="">Not applicable</option>
        <option value="BAA">BAA</option>
        <option value="DPA">DPA</option>
        <option value="both">Both</option>
      </select>
    </label>
    <label className="block text-sm font-medium text-slate-700">
      Contract renewal date
      <input
        type="date"
        value={form.contract_renewal_date ?? ""}
        onChange={(e) => onChange({ ...form, contract_renewal_date: e.target.value || null })}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
    </label>
    <label className="block text-sm font-medium text-slate-700">
      Contact email
      <input
        type="email"
        value={form.contact_email ?? ""}
        onChange={(e) => onChange({ ...form, contact_email: e.target.value || null })}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
    </label>
    <label className="block text-sm font-medium text-slate-700">
      Notes
      <textarea
        rows={4}
        value={form.notes ?? ""}
        onChange={(e) => onChange({ ...form, notes: e.target.value || null })}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
    </label>
  </>
);
