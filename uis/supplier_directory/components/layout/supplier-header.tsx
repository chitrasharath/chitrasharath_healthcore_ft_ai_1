import { HealthcoreLogo } from "@backoffice/supplier-directory/components/layout/healthcore-logo";

export const SupplierHeader = () => (
  <header className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8">
    <div className="flex items-center gap-3">
      <HealthcoreLogo />
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
    </div>
    <h1 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">Supplier Directory</h1>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-sky-100">
      Centralized registry for procurement and compliance across USA and UK clinic operations.
    </p>
  </header>
);
