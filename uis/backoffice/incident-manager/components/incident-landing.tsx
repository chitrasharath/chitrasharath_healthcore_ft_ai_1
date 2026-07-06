"use client";

import { HealthcoreLogo } from "@/components/layout/healthcore-logo";

import { IncidentNavCards } from "@backoffice/incident-manager/components/incident-nav-cards";

export const IncidentLanding = () => (
  <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
    <section className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10">
      <div className="flex items-center justify-center gap-3">
        <HealthcoreLogo />
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
      </div>
      <h1 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">Incident Manager</h1>
      <p className="mx-auto mt-2 max-w-3xl text-sm leading-6 text-sky-100">
        Log, track, and manage patient incidents across all HealthCore clinics.
      </p>
    </section>
    <IncidentNavCards />
  </main>
);
