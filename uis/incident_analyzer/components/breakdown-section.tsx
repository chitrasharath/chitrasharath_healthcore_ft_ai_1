import type { BreakdownItem } from "@/lib/types";

type BreakdownSectionProps = {
  title: string;
  items: BreakdownItem[];
  highlightLabel?: string;
};

export const BreakdownSection = ({ title, items, highlightLabel }: BreakdownSectionProps) => {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{title}</h2>
      <ul className="mt-4 space-y-3">
        {items.map((item) => {
          const pct = item.percentage ?? 0;
          const highlighted = item.label === highlightLabel;
          return (
            <li
              key={item.label}
              className={`rounded-lg px-3 py-2 ${highlighted ? "border-l-4 border-amber-500 bg-amber-50" : ""}`}
            >
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-800">{item.label}</span>
                <span className="text-slate-600">
                  {item.count} ({pct.toFixed(1)}%)
                </span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-sky-600" style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </article>
  );
};
