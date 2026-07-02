import Link from "next/link";

type IncidentPageHeaderProps = {
  title: string;
  backHref?: string;
  backLabel?: string;
};

export const IncidentPageHeader = ({
  title,
  backHref = "/incident-manager",
  backLabel = "← Back to Incident Manager",
}: IncidentPageHeaderProps) => (
  <div className="space-y-2">
    <Link href={backHref} className="text-sm font-medium text-sky-700 hover:text-sky-900">
      {backLabel}
    </Link>
    <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">{title}</h1>
  </div>
);
