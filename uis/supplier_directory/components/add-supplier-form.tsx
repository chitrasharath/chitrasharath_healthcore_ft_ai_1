"use client";

import { useState } from "react";

import { AddSupplierOptionalSection } from "@backoffice/supplier-directory/components/add-supplier-optional-section";
import { CategoryPicker } from "@backoffice/supplier-directory/components/category-picker";
import { CompliancePrompt } from "@backoffice/supplier-directory/components/compliance-prompt";
import { SupplierBasicFields } from "@backoffice/supplier-directory/components/supplier-basic-fields";
import type { SupplierCreateInput } from "@backoffice/supplier-directory/lib/types";

type AddSupplierFormProps = {
  onSubmit: (input: SupplierCreateInput) => Promise<void>;
};

const emptyForm = (): SupplierCreateInput => ({
  name: "",
  country: "USA",
  categories: [],
  monthly_rate: 0,
  currency: "USD",
  status: "active",
  compliance_agreement: null,
  contract_renewal_date: null,
  contact_email: null,
  notes: null,
});

export const AddSupplierForm = ({ onSubmit }: AddSupplierFormProps) => {
  const [form, setForm] = useState<SupplierCreateInput>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const toggleCategory = (category: string) => {
    setForm((current) => ({
      ...current,
      categories: current.categories.includes(category)
        ? current.categories.filter((c) => c !== category)
        : [...current.categories, category],
    }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form);
      setForm(emptyForm());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create supplier");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold text-slate-900">Register new supplier</h2>
      <SupplierBasicFields form={form} onChange={setForm} />
      <CategoryPicker selected={form.categories} onToggle={toggleCategory} />
      <CompliancePrompt categories={form.categories} />
      <AddSupplierOptionalSection form={form} onChange={setForm} />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <button
        type="submit"
        disabled={saving || form.categories.length === 0}
        className="rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Add supplier"}
      </button>
    </form>
  );
};
