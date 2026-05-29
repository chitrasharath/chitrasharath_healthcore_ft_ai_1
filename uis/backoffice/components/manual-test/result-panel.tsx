import { formatJson } from "@/lib/format-json";
import type { OperationResult } from "@/lib/operation-types";

type ResultPanelProps = {
  latestResult: OperationResult | null;
};

export function ResultPanel({ latestResult }: ResultPanelProps) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Latest operation result</h2>
      <p className="mt-2 text-xs text-slate-600">
        {latestResult ? latestResult.label : "No operation executed yet."}
      </p>
      <pre className="mt-3 min-h-[200px] overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
        {latestResult ? formatJson(latestResult.value) : "{}"}
      </pre>
    </article>
  );
}
