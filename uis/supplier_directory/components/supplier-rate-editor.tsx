"use client";

import { useState } from "react";

type SupplierRateEditorProps = {
  currentRate: number;
  onSave: (rate: number) => Promise<void>;
};

export const SupplierRateEditor = ({ currentRate, onSave }: SupplierRateEditorProps) => {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(String(currentRate));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Rate must be greater than 0");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(parsed);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update rate");
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => {
          setValue(String(currentRate));
          setOpen(true);
        }}
        className="rounded-lg bg-sky-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-sky-800"
      >
        Edit rate
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-24 rounded border border-slate-300 px-2 py-1 text-xs"
        />
        <button
          type="button"
          disabled={saving}
          onClick={() => void handleSave()}
          className="rounded bg-sky-700 px-2 py-1 text-xs font-semibold text-white"
        >
          Save
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-slate-500">
          Cancel
        </button>
      </div>
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </div>
  );
};
