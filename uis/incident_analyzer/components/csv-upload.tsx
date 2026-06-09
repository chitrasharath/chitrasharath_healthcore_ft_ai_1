"use client";

type CsvUploadProps = {
  disabled: boolean;
  onFileSelected: (file: File) => void;
};

export const CsvUpload = ({ disabled, onFileSelected }: CsvUploadProps) => {
  const handleFile = (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      return;
    }
    onFileSelected(file);
  };

  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-white p-6">
      <p className="text-sm text-slate-600">Upload an incidents CSV to analyze.</p>
      <label
        className={`mt-4 flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-6 py-10 text-center ${
          disabled ? "pointer-events-none opacity-60" : "hover:border-sky-400"
        }`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (!disabled) handleFile(event.dataTransfer.files[0]);
        }}
      >
        <span className="text-sm font-medium text-slate-800">Drop CSV here or click to browse</span>
        <span className="text-xs text-slate-500">UTF-8 comma-separated file only</span>
        <input
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          disabled={disabled}
          onChange={(event) => handleFile(event.target.files?.[0])}
        />
      </label>
    </section>
  );
};
