import type { SupplierCreateInput } from "@/lib/types";

import { SupplierOptionalFields } from "@/components/supplier-optional-fields";

type AddSupplierOptionalSectionProps = {
  form: SupplierCreateInput;
  onChange: (form: SupplierCreateInput) => void;
};

export const AddSupplierOptionalSection = ({ form, onChange }: AddSupplierOptionalSectionProps) => (
  <fieldset className="space-y-4 rounded-xl border border-slate-200 p-4">
    <legend className="px-1 text-sm font-semibold text-slate-800">Optional details</legend>
    <SupplierOptionalFields
      form={form}
      onChange={(optional) => onChange({ ...form, ...optional })}
    />
  </fieldset>
);
