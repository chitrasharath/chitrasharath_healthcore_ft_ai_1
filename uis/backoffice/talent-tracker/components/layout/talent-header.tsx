import { HealthcoreLogo } from "@backoffice/talent-tracker/components/layout/healthcore-logo";

type TalentHeaderProps = {
  totalCandidates?: number;
};

export const TalentHeader = ({ totalCandidates }: TalentHeaderProps) => (
  <header className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8">
    <div className="flex items-center gap-3">
      <HealthcoreLogo />
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
    </div>
    <h1 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">Talent Pipeline Tracker</h1>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-sky-100">
      {typeof totalCandidates === "number"
        ? `${totalCandidates} total candidates in the recruiting pipeline.`
        : "Track recruitment and hiring pipeline across HealthCore operations."}
    </p>
  </header>
);
