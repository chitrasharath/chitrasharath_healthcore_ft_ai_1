"use client";

import type { ChangeEvent } from "react";

type Props = {
  uploading: boolean;
  onUpload: (file: File) => void;
  onRunAll: (file: File) => void;
};

const MAX_BYTES = 20 * 1024 * 1024;

const pickPdf = (
  event: ChangeEvent<HTMLInputElement>,
  handler: (file: File) => void,
) => {
  const file = event.target.files?.[0];
  if (!file) return;
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    window.alert("Only PDF files are accepted.");
    return;
  }
  if (file.size > MAX_BYTES) {
    window.alert("PDF must be 20 MB or smaller.");
    return;
  }
  handler(file);
  event.target.value = "";
};

export const RfpUploadForm = ({ uploading, onUpload, onRunAll }: Props) => (
  <div className="grid gap-3 sm:grid-cols-2">
    <label className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-sky-300 bg-sky-50 px-4 py-6 text-sm text-slate-700">
      <span className="font-medium text-sky-900">
        Upload RFP (Phase 1 start and rest of phases are step by step)
      </span>
      <span className="text-slate-600">Max 20 MB. Intake starts immediately.</span>
      <input
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        disabled={uploading}
        onChange={(event) => pickPdf(event, onUpload)}
      />
      <span className="text-sky-800">{uploading ? "Working…" : "Choose PDF"}</span>
    </label>
    <label className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-teal-400 bg-teal-50 px-4 py-6 text-sm text-slate-700">
      <span className="font-medium text-teal-900">Run all phases</span>
      <span className="text-slate-600">
        PDF → intake → drafting → approval (halts for humans).
      </span>
      <input
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        disabled={uploading}
        onChange={(event) => pickPdf(event, onRunAll)}
      />
      <span className="text-teal-800">{uploading ? "Working…" : "Choose PDF & run all"}</span>
    </label>
  </div>
);
