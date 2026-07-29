"use client";

import { useCallback, useEffect, useState } from "react";

import { deleteMemory, listMemories } from "../lib/knowledge-api";
import type { MemoryListItem } from "../types/knowledge";

export const MemoryPanel = () => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<MemoryListItem[]>([]);
  const [clinicId, setClinicId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listMemories();
      setItems(data.memories);
      setClinicId(data.clinic_id);
      setError(null);
    } catch {
      setError("Could not load memories.");
    }
  }, []);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  const onDelete = async (id: string) => {
    try {
      await deleteMemory(id);
      await refresh();
    } catch {
      setError("Could not delete memory.");
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <button
        type="button"
        className="text-sm font-semibold text-sky-800 dark:text-sky-300"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? "Hide" : "Show"} what I remember for this clinic
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          {clinicId ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">Clinic {clinicId}</p>
          ) : null}
          {error ? (
            <p className="text-xs text-red-700 dark:text-red-300" role="alert">{error}</p>
          ) : null}
          {items.length === 0 && !error ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No saved memories yet.</p>
          ) : null}
          <ul className="space-y-2">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 p-2 text-sm dark:border-slate-800"
              >
                <span className="text-slate-800 dark:text-slate-100">{item.text}</span>
                <button
                  type="button"
                  className="shrink-0 text-xs text-red-700 dark:text-red-300"
                  onClick={() => void onDelete(item.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
};
