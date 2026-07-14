type Props = { title: string; value: string; detail?: string };

export const KpiHeadline = ({ title, value, detail }: Props) => (
  <div className="rounded-xl bg-gradient-to-r from-sky-900 to-teal-700 px-5 py-4 text-white shadow">
    <p className="text-xs font-semibold uppercase tracking-[0.15em] text-sky-100">{title}</p>
    <p className="mt-1 text-3xl font-extrabold tracking-tight">{value}</p>
    {detail ? <p className="mt-1 text-sm text-sky-100">{detail}</p> : null}
  </div>
);
