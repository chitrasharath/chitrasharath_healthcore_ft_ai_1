type ApiFilterToggleProps = {
  enabled: boolean;
  onToggle: () => void;
};

export const ApiFilterToggle = ({ enabled, onToggle }: ApiFilterToggleProps) => {
  const tooltip = enabled ? "Server-side filtering" : "Client-side filtering";

  return (
    <div className="group relative">
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={enabled}
        aria-label={tooltip}
        title={tooltip}
        className={
          enabled
            ? "inline-flex h-10 w-10 items-center justify-center rounded-lg border border-sky-600 bg-sky-50 text-sky-700 hover:bg-sky-100"
            : "inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-500 hover:bg-slate-50"
        }
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.75">
          <path strokeLinecap="round" d="M7 8h10M7 12h6M7 16h8" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z" />
          <circle cx="17" cy="8" r="1.25" fill="currentColor" stroke="none" />
          <circle cx="17" cy="12" r="1.25" fill="currentColor" stroke="none" />
          <circle cx="17" cy="16" r="1.25" fill="currentColor" stroke="none" />
        </svg>
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {tooltip}
      </span>
    </div>
  );
};
