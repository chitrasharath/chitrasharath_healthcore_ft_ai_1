import { HealthcoreLogo } from "@backoffice/backoffice-functions/components/layout/healthcore-logo";

export function BackofficeHeader() {
  return (
    <header className="mb-8 rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8">
      <div className="flex items-center gap-3">
        <HealthcoreLogo />
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
      </div>
      <h1 className="mt-4 text-2xl font-extrabold tracking-tight md:text-3xl">Milestone 2 Function Manual Test</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-sky-100">
        This page renders outputs from the TypeScript utility functions using the sample data from the context file.
      </p>
    </header>
  );
}
