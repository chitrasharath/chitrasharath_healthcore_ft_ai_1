type Props = { text: string };

export const KpiDefinition = ({ text }: Props) => (
  <p className="rounded-lg border border-sky-100 bg-sky-50 px-4 py-3 text-sm leading-6 text-slate-700">
    {text}
  </p>
);
