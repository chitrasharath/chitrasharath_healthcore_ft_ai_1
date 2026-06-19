import Link from "next/link";

import { HealthcoreLogo } from "@/components/layout/healthcore-logo";
import type { UserProfile } from "@/lib/api";

type LandingHeroProps = {
  user: UserProfile | null;
  onLogout: () => void;
};

export const LandingHero = ({ user, onLogout }: LandingHeroProps) => (
  <section className="rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10">
    <div className="mb-6 flex items-center justify-center gap-3">
      <HealthcoreLogo />
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">HealthCore Digital</p>
    </div>
    {user ? (
      <p className="text-sm font-medium text-sky-100">Welcome, {user.name || user.email}</p>
    ) : null}
    <h1 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">HealthCore Back Office</h1>
    <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-sky-100">
      Secure portal for HealthCore internal tools and administration.
    </p>
    <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
      {user ? (
        <>
          <Link
            href="/account/profile"
            className="rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-sky-900 transition hover:bg-sky-50"
          >
            My Profile
          </Link>
          <button
            type="button"
            onClick={onLogout}
            className="rounded-lg border border-white px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Log Out
          </button>
        </>
      ) : (
        <>
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
        </>
      )}
    </div>
  </section>
);
