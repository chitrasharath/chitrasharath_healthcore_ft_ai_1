import Link from "next/link";

import { HealthcoreLogo } from "@/components/layout/healthcore-logo";

export default function LandingPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      <section className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10">
        <div className="mb-6 flex items-center justify-center gap-3">
          <HealthcoreLogo />
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">HealthCore Back Office</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-sky-100">
          Secure portal for HealthCore internal tools and administration.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/login"
            className="rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-sky-900 transition hover:bg-sky-50"
          >
            Log In
          </Link>
          <Link
            href="/register"
            className="rounded-lg border border-white px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Register
          </Link>
        </div>
      </section>
    </main>
  );
}
