import { formatJson } from "@backoffice/backoffice-functions/lib/format-json";
import type { OperationResult } from "@backoffice/backoffice-functions/lib/operation-types";

type ResultPanelProps = {
  latestResult: OperationResult | null;
};

export function ResultPanel({ latestResult }: ResultPanelProps) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-bold text-sky-800">Latest operation result</h2>
      <p className="mt-2 text-xs text-slate-600">
        {latestResult ? latestResult.label : "No operation executed yet."}
      </p>
      <pre className="mt-3 min-h-[200px] overflow-auto rounded-lg bg-sky-950 p-3 text-xs text-sky-50">
        {latestResult ? formatJson(latestResult.value) : "{}"}
      </pre>
    </article>
  );
}
