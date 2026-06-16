import type { SupplierCreateInput } from "@/lib/types";

import { currencyForCountry } from "@/lib/categories";

type SupplierBasicFieldsProps = {
  form: SupplierCreateInput;
  onChange: (form: SupplierCreateInput) => void;
};

export const SupplierBasicFields = ({ form, onChange }: SupplierBasicFieldsProps) => (
  <>
    <div className="grid gap-4 md:grid-cols-2">
      <label className="text-sm font-medium text-slate-700">
        Name
        <input
          required
          value={form.name}
          onChange={(e) => onChange({ ...form, name: e.target.value })}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="text-sm font-medium text-slate-700">
        Country
        <select
          value={form.country}
          onChange={(e) => {
            const country = e.target.value as "USA" | "UK";
            onChange({ ...form, country, currency: currencyForCountry(country) });
          }}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="USA">USA</option>
          <option value="UK">UK</option>
        </select>
      </label>
    </div>
    <div className="grid gap-4 md:grid-cols-3">
      <label className="text-sm font-medium text-slate-700">
        Monthly rate
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          value={form.monthly_rate || ""}
          onChange={(e) => onChange({ ...form, monthly_rate: Number(e.target.value) })}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="text-sm font-medium text-slate-700">
        Status
        <select
          value={form.status}
          onChange={(e) => onChange({ ...form, status: e.target.value as "active" | "suspended" })}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
      </label>
      <label className="text-sm font-medium text-slate-700">
        Compliance
        <select
          value={form.compliance_agreement ?? ""}
          onChange={(e) => onChange({ ...form, compliance_agreement: e.target.value || null })}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">N/A</option>
          <option value="BAA">BAA</option>
          <option value="DPA">DPA</option>
          <option value="both">Both</option>
        </select>
      </label>
    </div>
  </>
);
