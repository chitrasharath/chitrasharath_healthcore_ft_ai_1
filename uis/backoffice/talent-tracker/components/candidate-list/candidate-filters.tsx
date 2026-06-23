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
    <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
      <div className="flex flex-col gap-2 md:flex-row md:flex-nowrap md:items-center">
        <input
          value={search}
          onChange={(event) => onChange("search", event.target.value)}
          placeholder="Search name or email"
          className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm text-slate-900 outline-none ring-sky-600 focus:ring-2 md:w-44 md:shrink-0"
        />
        <select
          value={status || "all"}
          onChange={(event) => onChange("status", event.target.value)}
          className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm text-slate-900 outline-none ring-sky-600 focus:ring-2 md:w-36 md:shrink-0"
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
          className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm text-slate-900 outline-none ring-sky-600 focus:ring-2 md:w-36 md:shrink-0"
        >
          <option value="all">All stage</option>
          <option value="pending">Pending</option>
          <option value="review">Review</option>
          <option value="personal_interview">Personal</option>
          <option value="technical_interview">Technical</option>
          <option value="offer_presented">Offer</option>
        </select>
        <button
          type="button"
          onClick={onClear}
          className="w-full shrink-0 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm font-semibold whitespace-nowrap text-slate-700 hover:bg-slate-50 md:w-auto"
        >
          Clear
        </button>
      </div>
    </section>
  );
};
