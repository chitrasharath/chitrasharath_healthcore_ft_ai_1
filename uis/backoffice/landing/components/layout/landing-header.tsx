import { HealthcoreLogo } from "@/components/layout/healthcore-logo";

export const LandingHeader = () => (
  <header className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8">
    <div className="flex items-center gap-3">
      <HealthcoreLogo />
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
    </div>
  </header>
);
