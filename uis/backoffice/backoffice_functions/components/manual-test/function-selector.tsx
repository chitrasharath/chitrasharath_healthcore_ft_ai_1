import type { OperationDefinition } from "@/lib/operation-types";

type FunctionSelectorProps = {
  operations: OperationDefinition[];
  selectedId: string;
  description: string;
  onSelect: (id: string) => void;
};

export function FunctionSelector({ operations, selectedId, description, onSelect }: FunctionSelectorProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-500" htmlFor="function-select">
        Function
        <select
          id="function-select"
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
        >
          {operations.map((op) => (
            <option key={op.id} value={op.id}>
              {op.label}
            </option>
          ))}
        </select>
      </label>
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Function info</h3>
        <p className="mt-2 text-sm text-slate-700">{description}</p>
      </div>
    </div>
  );
}
