"use client";

import { useState } from "react";

import { SupplierRateEditor } from "@/components/supplier-rate-editor";
import type { Supplier } from "@/lib/types";

type SupplierRowActionsProps = {
  supplier: Supplier;
  onUpdateRate: (id: number, rate: number) => Promise<void>;
  onToggleStatus: (supplier: Supplier) => Promise<void>;
};

export const SupplierRowActions = ({
  supplier,
  onUpdateRate,
  onToggleStatus,
}: SupplierRowActionsProps) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = async () => {
    setBusy(true);
    setError(null);
    try {
      await onToggleStatus(supplier);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update status");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <SupplierRateEditor
          currentRate={supplier.monthly_rate}
          onSave={(rate) => onUpdateRate(supplier.id, rate)}
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => void handleToggle()}
          className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          {supplier.status === "active" ? "Suspend" : "Activate"}
        </button>
      </div>
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </div>
  );
};
