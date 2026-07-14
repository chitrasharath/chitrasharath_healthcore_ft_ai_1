import { HealthcoreLogo } from "@/components/layout/healthcore-logo";

export const ReportingHero = () => (
  <section className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10">
    <div className="flex items-center justify-center gap-3">
      <HealthcoreLogo />
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
    </div>
    <h1 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">Reporting</h1>
    <p className="mx-auto mt-2 max-w-3xl text-sm leading-6 text-sky-100">
      Materialized telemetry KPIs and pipeline health from nightly ETL.
    </p>
  </section>
);
