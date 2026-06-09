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
      className="rounded-md bg-sky-700 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-sky-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
    >
      {exporting ? "Exporting…" : "Export results to CSV"}
    </button>
  );
};
