"use client";

import { HealthcoreLogo } from "@/components/layout/healthcore-logo";

import { InventoryNavCards } from "@backoffice/inventory/components/inventory-nav-cards";

export const InventoryLanding = () => (
  <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
    <section className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10">
      <div className="mb-6 flex items-center justify-center gap-3">
        <HealthcoreLogo />
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
      </div>
      <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">Medical Supply Inventory</h1>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-sky-100">
        Track stock levels, log deliveries, and record clinical consumption across all HealthCore clinics.
      </p>
    </section>
    <InventoryNavCards />
  </main>
);
