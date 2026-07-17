import type { PipelineRunLatest } from "@backoffice/reporting/types/reporting";

const statusClass = (status: string): string => {
  if (status === "success") return "text-emerald-700";
  if (status === "partial") return "text-amber-700";
  if (status === "quarantined") return "text-orange-700";
  if (status === "failed") return "text-rose-700";
  return "text-slate-700";
};

const shortId = (runId: string): string => runId.slice(0, 8);

const fmtWhen = (iso: string | null): string => {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 16);
};

type Props = { runs: PipelineRunLatest[] };

export const PipelineRecentRuns = ({ runs }: Props) => {
  if (runs.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-800">Recent runs</h3>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 font-semibold">Started</th>
              <th className="px-3 py-2 font-semibold">Status</th>
              <th className="px-3 py-2 font-semibold">Loaded</th>
              <th className="px-3 py-2 font-semibold">Checkpoint</th>
              <th className="px-3 py-2 font-semibold">Run</th>
              <th className="px-3 py-2 font-semibold">Notes</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((row) => (
              <tr key={row.run_id} className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-700">{fmtWhen(row.started_at)}</td>
                <td className={`px-3 py-2 font-medium capitalize ${statusClass(row.status)}`}>
                  {row.status}
                </td>
                <td className="px-3 py-2 text-slate-700">{row.rows_loaded}</td>
                <td className="px-3 py-2 text-slate-700">{row.checkpoint ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-600">{shortId(row.run_id)}</td>
                <td className="max-w-xs truncate px-3 py-2 text-slate-600">
                  {row.error_summary ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
