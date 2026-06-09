import type { Satisfaction } from "@/lib/types";

type SatisfactionSectionProps = {
  satisfaction: Satisfaction;
};

export const SatisfactionSection = ({ satisfaction }: SatisfactionSectionProps) => {
  const maxCount = Math.max(...satisfaction.distribution.map((item) => item.count), 1);

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
        Satisfaction index (closed cases)
      </h2>
      <p className="mt-3 text-sm text-slate-600">
        Scored cases: {satisfaction.scored_cases} of {satisfaction.total_closed}
      </p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">
        {satisfaction.average?.toFixed(2) ?? "—"} / {satisfaction.max_score.toFixed(2)}
      </p>
      <ul className="mt-4 space-y-2">
        {satisfaction.distribution.map((item) => (
          <li key={item.score} className="text-sm text-slate-700">
            <div className="flex justify-between">
              <span>
                Score {item.score} ({item.label})
              </span>
              <span className="font-medium">{item.count}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-slate-100">
              <div
                className="h-1.5 rounded-full bg-emerald-600"
                style={{ width: `${(item.count / maxCount) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </article>
  );
};
