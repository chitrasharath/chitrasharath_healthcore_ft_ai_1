import type { OperationResult } from "@backoffice/backoffice-functions/lib/operation-types";

type HistoryPanelProps = {
  history: OperationResult[];
};

export function HistoryPanel({ history }: HistoryPanelProps) {
  const reversed = [...history].reverse();

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-bold text-sky-800">Execution history</h2>
      <ul className="mt-3 space-y-2 text-xs text-slate-700">
        {reversed.length === 0 ? null : reversed.map((entry, index) => (
          <li key={`${entry.label}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-2">
            <span className="font-semibold text-slate-900">
              {history.length - index}. {entry.label}
            </span>
          </li>
        ))}
      </ul>
    </article>
  );
}
