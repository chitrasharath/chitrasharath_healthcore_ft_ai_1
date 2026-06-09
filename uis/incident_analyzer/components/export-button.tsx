"use client";

type ExportButtonProps = {
  disabled: boolean;
  exporting: boolean;
  onExport: () => void;
};

export const ExportButton = ({ disabled, exporting, onExport }: ExportButtonProps) => {
  return (
    <button
      type="button"
      disabled={disabled || exporting}
      onClick={onExport}
      className="rounded-lg bg-sky-700 px-4 py-2 text-sm font-medium text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-300"
    >
      {exporting ? "Exporting…" : "Export results to CSV"}
    </button>
  );
};
