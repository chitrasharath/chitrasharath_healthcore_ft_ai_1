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
    <section className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((card) => (
          <article key={card.key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">{card.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{totals[card.field]}</p>
          </article>
        ))}
      </div>
      {totals.invalid > 0 ? (
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
            Invalid records breakdown
          </h2>
          <ul className="mt-3 space-y-2">
            {invalidBreakdown.map((item) => (
              <li key={item.rule} className="flex justify-between text-sm text-slate-700">
                <span>{item.label}</span>
                <span className="font-medium">{item.count}</span>
              </li>
            ))}
          </ul>
        </article>
      ) : null}
    </section>
  );
};
