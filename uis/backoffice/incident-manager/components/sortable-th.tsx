import type { IncidentSortKey, SortDirection } from "@backoffice/incident-manager/lib/sort-incidents";

type SortableThProps = {
  label: string;
  column: IncidentSortKey;
  sortKey: IncidentSortKey;
  sortDirection: SortDirection;
  onSort: (key: IncidentSortKey) => void;
};

const SortArrow = ({ direction, active }: { direction: "up" | "down"; active: boolean }) => (
  <svg
    aria-hidden="true"
    className={`h-2.5 w-2.5 ${active ? "text-sky-700" : "text-slate-300"}`}
    viewBox="0 0 10 6"
    fill="currentColor"
  >
    {direction === "up" ? (
      <path d="M5 0 0 5.5h10L5 0z" />
    ) : (
      <path d="M5 6 10 0.5H0L5 6z" />
    )}
  </svg>
);

export const SortableTh = ({
  label,
  column,
  sortKey,
  sortDirection,
  onSort,
}: SortableThProps) => {
  const active = sortKey === column;

  return (
    <th className="px-2 pb-3 text-center">
      <button
        type="button"
        onClick={() => onSort(column)}
        className={`inline-flex items-center justify-center gap-1 text-xs font-semibold uppercase tracking-wide ${
          active ? "text-sky-800" : "text-slate-500 hover:text-sky-700"
        }`}
        aria-sort={active ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}
      >
        <span>{label}</span>
        <span className="inline-flex flex-col gap-px">
          <SortArrow direction="up" active={active && sortDirection === "asc"} />
          <SortArrow direction="down" active={active && sortDirection === "desc"} />
        </span>
      </button>
    </th>
  );
};
