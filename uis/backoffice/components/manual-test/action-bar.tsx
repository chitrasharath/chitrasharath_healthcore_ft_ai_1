type ActionBarProps = {
  onRunSelected: () => void;
  onRunAll: () => void;
  onClear: () => void;
};

export function ActionBar({ onRunSelected, onRunAll, onClear }: ActionBarProps) {
  return (
    <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-200 pt-4">
      <button
        type="button"
        onClick={onRunSelected}
        className="rounded-lg bg-indigo-700 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-600"
      >
        Run selected function
      </button>
      <button
        type="button"
        onClick={onRunAll}
        className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
      >
        Run all with current defaults
      </button>
      <button
        type="button"
        onClick={onClear}
        className="rounded-lg bg-slate-200 px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-300"
      >
        Clear output
      </button>
    </div>
  );
}
