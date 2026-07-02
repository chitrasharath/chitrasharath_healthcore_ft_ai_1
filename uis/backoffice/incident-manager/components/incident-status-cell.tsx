import { STATUS_TRANSITIONS, STATUSES } from "@backoffice/incident-manager/lib/constants";
import { IncidentStatusBadge } from "@backoffice/incident-manager/components/incident-status-badge";

type IncidentStatusCellProps = {
  id: number;
  status: string;
  onChange: (id: number, status: string) => void;
};

export const IncidentStatusCell = ({ id, status, onChange }: IncidentStatusCellProps) => {
  const options = STATUS_TRANSITIONS[status] ?? [];
  return (
    <div className="flex flex-col gap-2">
      <IncidentStatusBadge status={status} />
      {options.length > 0 ? (
        <select
          className="rounded border border-slate-300 px-2 py-1 text-xs"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value) onChange(id, e.target.value);
            e.target.value = "";
          }}
        >
          <option value="">Update status…</option>
          {options.map((value) => (
            <option key={value} value={value}>
              {STATUSES.find((s) => s.value === value)?.label ?? value}
            </option>
          ))}
        </select>
      ) : null}
    </div>
  );
};
