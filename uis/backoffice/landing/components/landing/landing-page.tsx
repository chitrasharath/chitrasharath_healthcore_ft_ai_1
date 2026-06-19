"use client";

import { LandingHero } from "@/components/landing/landing-hero";
import { NavCards } from "@/components/landing/nav-cards";
import { PublicIntro } from "@/components/landing/public-intro";
import { useLandingSession } from "@/hooks/use-landing-session";

export const LandingPage = () => {
  const { user, token, loading, logout } = useLandingSession();

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      <LandingHero user={user} onLogout={logout} />
      {loading ? (
        <p className="mt-8 text-center text-sm text-slate-500">Loading…</p>
      ) : user && token ? (
        <NavCards token={token} />
      ) : (
        <PublicIntro />
      )}
    </main>
  );
};
