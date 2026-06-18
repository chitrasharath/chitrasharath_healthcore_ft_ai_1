import { HealthcoreLogo } from "@/components/layout/healthcore-logo";

type IncidentHeaderProps = {
  sourceFilename?: string;
  analyzedAt?: string;
};

export const IncidentHeader = ({ sourceFilename, analyzedAt }: IncidentHeaderProps) => {
  return (
    <header className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8">
      <div className="flex items-center gap-3">
        <HealthcoreLogo />
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
      </div>
      <h1 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">
        Patient Incident Report Analysis
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-sky-100">
        Upload an incidents CSV to analyze HIPAA-safe aggregate metrics for Patient Experience reporting.
      </p>
      {sourceFilename && analyzedAt ? (
        <p className="mt-3 text-xs text-sky-200">
          Source: {sourceFilename} · Analyzed: {new Date(analyzedAt).toLocaleString()}
        </p>
      ) : null}
    </header>
  );
};
