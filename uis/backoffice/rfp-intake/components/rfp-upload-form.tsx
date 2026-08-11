"use client";

import type { ChangeEvent } from "react";

type Props = {
  uploading: boolean;
  onUpload: (file: File) => void;
};

const MAX_BYTES = 20 * 1024 * 1024;

export const RfpUploadForm = ({ uploading, onUpload }: Props) => {
  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
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
    onUpload(file);
    event.target.value = "";
  };

  return (
    <label className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-sky-300 bg-sky-50 px-4 py-6 text-sm text-slate-700">
      <span className="font-medium text-sky-900">Upload institutional RFP (PDF)</span>
      <span className="text-slate-600">Max 20 MB. Processing starts immediately.</span>
      <input
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        disabled={uploading}
        onChange={onChange}
      />
      <span className="text-sky-800">{uploading ? "Uploading…" : "Choose PDF"}</span>
    </label>
  );
};
