type LabelOption = { value: string; label: string };

type SummarySectionProps = {
  title: string;
  data: Record<string, number>;
  labels: readonly LabelOption[];
  dynamicOnly?: boolean;
};

export const SummarySection = ({ title, data, labels, dynamicOnly = false }: SummarySectionProps) => {
  const entries = dynamicOnly
    ? Object.entries(data).filter(([, count]) => count > 0)
    : labels.map((item) => [item.value, data[item.value] ?? 0] as const);

  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-bold text-sky-800">{title}</h2>
      <ul className="mt-4 space-y-3">
        {entries.map(([key, count]) => {
          const label = labels.find((l) => l.value === key)?.label ?? key;
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <li key={key}>
              <div className="flex justify-between text-sm text-slate-700">
                <span>{label}</span>
                <span className="font-semibold text-slate-900">{count}</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-sky-700" style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </article>
  );
};
