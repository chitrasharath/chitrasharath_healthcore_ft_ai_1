"use client";

import { Suspense } from "react";

import { InventoryPageHeader } from "@backoffice/inventory/components/inventory-page-header";
import { OutboundFormFieldsShell as OutboundFormFields } from "@backoffice/inventory/components/outbound-form-fields-shell";
import { StatusBanner } from "@backoffice/inventory/components/status-banner";
import { useOutboundForm } from "@backoffice/inventory/hooks/use-outbound-form";

const OutboundOrderFormContent = () => {
  const form = useOutboundForm();

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <InventoryPageHeader
        title="Log Consumption"
        subtitle="Record clinical use or waste of medical supplies."
      />
      {form.success ? <StatusBanner variant="success" message={form.success} /> : null}
      {form.formError ? <StatusBanner variant="error" message={form.formError} /> : null}
      <form
        onSubmit={(e) => void form.handleSubmit(e)}
        className="mt-4 space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        {form.loadingProducts ? (
          <p className="text-sm text-slate-500">Loading supplies…</p>
        ) : (
          <OutboundFormFields
            products={form.products}
            supplyId={form.supplyId}
            onSupplyIdChange={form.setSupplyId}
            quantity={form.quantity}
            onQuantityChange={form.setQuantity}
            consumptionType={form.consumptionType}
            onConsumptionTypeChange={form.setConsumptionType}
            clinicId={form.clinicId}
            onClinicIdChange={form.setClinicId}
            stock={form.stock}
            unit={form.unit}
            loadingStock={form.loadingStock}
            showStockWarning={form.showStockWarning}
            quantityError={form.quantityError}
            disabled={form.saving}
          />
        )}
        <button
          type="submit"
          disabled={form.saving || form.loadingProducts}
          className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
        >
          {form.saving ? "Saving…" : "Log Consumption"}
        </button>
      </form>
    </main>
  );
};

export const OutboundOrderForm = () => (
  <Suspense fallback={<p className="px-4 py-8 text-sm text-slate-500">Loading form…</p>}>
    <OutboundOrderFormContent />
  </Suspense>
);
