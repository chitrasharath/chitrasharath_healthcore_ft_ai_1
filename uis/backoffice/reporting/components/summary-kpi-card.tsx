import type { SummaryKpiCard } from "@backoffice/reporting/lib/summary-series";

type Props = { card: SummaryKpiCard };

export const SummaryKpiCardView = ({ card }: Props) => (
  <article className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
    <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{card.title}</h2>
    <p className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900">{card.headline}</p>
    <p className="mt-0.5 text-xs text-slate-500">{card.detail}</p>
  </article>
);
