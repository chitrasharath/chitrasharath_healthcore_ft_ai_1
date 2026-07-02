import Link from "next/link";

const cardClass =
  "rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-sky-300 hover:shadow-md";

const CARDS = [
  {
    title: "Log Incident",
    description: "Report a new patient or operational incident",
    href: "/incident-manager/new",
  },
  {
    title: "Incident List",
    description: "View and filter all registered incidents",
    href: "/incident-manager/list",
  },
  {
    title: "Summary Dashboard",
    description: "Aggregated metrics by status, category, origin, and branch",
    href: "/incident-manager/summary",
  },
] as const;

export const IncidentNavCards = () => (
  <div className="grid gap-5 sm:grid-cols-3">
    {CARDS.map((card) => (
      <Link key={card.href} href={card.href} className={cardClass}>
        <h3 className="font-semibold text-slate-900">{card.title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
      </Link>
    ))}
  </div>
);
