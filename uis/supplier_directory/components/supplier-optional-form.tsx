"use client";

import { useState } from "react";

import { CompliancePrompt } from "@backoffice/supplier-directory/components/compliance-prompt";
import { SupplierOptionalFields } from "@backoffice/supplier-directory/components/supplier-optional-fields";
import type { Supplier, SupplierDetailsInput } from "@backoffice/supplier-directory/lib/types";

type SupplierOptionalFormProps = {
  supplier: Supplier;
  onSave: (details: SupplierDetailsInput) => Promise<void>;
};

const toForm = (supplier: Supplier): SupplierDetailsInput => ({
  compliance_agreement: supplier.compliance_agreement,
  contract_renewal_date: supplier.contract_renewal_date,
  contact_email: supplier.contact_email,
  notes: supplier.notes,
});

export const SupplierOptionalForm = ({ supplier, onSave }: SupplierOptionalFormProps) => {
  const [form, setForm] = useState<SupplierDetailsInput>(() => toForm(supplier));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await onSave(form);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save details");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-bold text-slate-900">Optional details</h3>
      <CompliancePrompt categories={supplier.categories} />
      <SupplierOptionalFields form={form} onChange={setForm} />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {saved ? <p className="text-sm text-emerald-700">Details saved.</p> : null}
      <button
        type="submit"
        disabled={saving}
        className="rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save details"}
      </button>
    </form>
  );
};
