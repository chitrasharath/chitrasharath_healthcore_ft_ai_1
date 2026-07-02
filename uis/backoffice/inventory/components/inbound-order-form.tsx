"use client";

import { Suspense } from "react";

import { InboundFormFields } from "@backoffice/inventory/components/inbound-form-fields-shell";
import { InventoryPageHeader } from "@backoffice/inventory/components/inventory-page-header";
import { StatusBanner } from "@backoffice/inventory/components/status-banner";
import { useInboundForm } from "@backoffice/inventory/hooks/use-inbound-form";

const InboundOrderFormContent = () => {
  const form = useInboundForm();

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <InventoryPageHeader
        title="Log Delivery"
        subtitle="Register an inbound supply delivery from a vendor."
      />
      {form.success ? <StatusBanner variant="success" message={form.success} /> : null}
      {form.error ? <StatusBanner variant="error" message={form.error} /> : null}
      <form
        onSubmit={(e) => void form.handleSubmit(e)}
        className="mt-4 space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        {form.loadingProducts ? (
          <p className="text-sm text-slate-500">Loading supplies…</p>
        ) : (
          <InboundFormFields
            products={form.products}
            supplyId={form.supplyId}
            onSupplyIdChange={form.setSupplyId}
            quantity={form.quantity}
            onQuantityChange={form.setQuantity}
            vendor={form.vendor}
            onVendorChange={form.setVendor}
            clinicId={form.clinicId}
            onClinicIdChange={form.setClinicId}
            disabled={form.saving}
          />
        )}
        <button
          type="submit"
          disabled={form.saving || form.loadingProducts}
          className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
        >
          {form.saving ? "Saving…" : "Log Delivery"}
        </button>
      </form>
    </main>
  );
};

export const InboundOrderForm = () => (
  <Suspense fallback={<p className="px-4 py-8 text-sm text-slate-500">Loading form…</p>}>
    <InboundOrderFormContent />
  </Suspense>
);
