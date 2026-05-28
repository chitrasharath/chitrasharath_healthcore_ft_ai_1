type CandidateFiltersProps = {
  search: string;
  status: string;
  stage: string;
  onChange: (key: string, value: string) => void;
  onClear: () => void;
};

export const CandidateFilters = ({
  search,
  status,
  stage,
  onChange,
  onClear,
}: CandidateFiltersProps) => {
  return (
    <section className="rounded-xl border border-[var(--hc-border)] bg-[var(--hc-surface)] p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <input
          value={search}
          onChange={(event) => onChange("search", event.target.value)}
          placeholder="Search by name or email"
          className="w-full flex-1 rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm outline-none ring-[var(--hc-brand)] focus:ring-2"
        />
        <select
          value={status || "all"}
          onChange={(event) => onChange("status", event.target.value)}
          className="w-full rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm outline-none ring-[var(--hc-brand)] focus:ring-2 md:w-44"
        >
          <option value="all">All status</option>
          <option value="received">Received</option>
          <option value="in_progress">In progress</option>
          <option value="selected">Selected</option>
          <option value="discarded">Discarded</option>
        </select>
        <select
          value={stage || "all"}
          onChange={(event) => onChange("stage", event.target.value)}
          className="w-full rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm outline-none ring-[var(--hc-brand)] focus:ring-2 md:w-48"
        >
          <option value="all">All stage</option>
          <option value="pending">Pending</option>
          <option value="review">Review</option>
          <option value="personal_interview">Personal interview</option>
          <option value="technical_interview">Technical interview</option>
          <option value="offer_presented">Offer presented</option>
        </select>
        <button
          type="button"
          onClick={onClear}
          className="rounded-md border border-[var(--hc-border)] bg-white px-3 py-2 text-sm font-semibold"
        >
          Clear Filters
        </button>
      </div>
    </section>
  );
};
