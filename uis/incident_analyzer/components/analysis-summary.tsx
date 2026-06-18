import type { InvalidBreakdownItem, Totals } from "@/lib/types";

type AnalysisSummaryProps = {
  totals: Totals;
  invalidBreakdown: InvalidBreakdownItem[];
};

const cards = [
  { key: "total", label: "Total records", field: "total" as const },
  { key: "valid", label: "Valid records", field: "valid" as const },
  { key: "invalid", label: "Invalid / incomplete", field: "invalid" as const },
];

export const AnalysisSummary = ({ totals, invalidBreakdown }: AnalysisSummaryProps) => {
  return (
    <section className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-3">
        {cards.map((card) => (
          <article key={card.key} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-600">{card.label}</p>
            <p className="mt-2 text-3xl font-extrabold tracking-tight text-sky-800">{totals[card.field]}</p>
          </article>
        ))}
      </div>
      {totals.invalid > 0 ? (
        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-bold text-sky-800">Invalid records breakdown</h2>
          <ul className="mt-3 space-y-2">
            {invalidBreakdown.map((item) => (
              <li key={item.rule} className="flex justify-between border-b border-slate-100 pb-2 text-sm text-slate-700 last:border-0">
                <span>{item.label}</span>
                <span className="font-semibold text-slate-900">{item.count}</span>
              </li>
            ))}
          </ul>
        </article>
      ) : null}
    </section>
  );
};
