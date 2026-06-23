import { NavCard } from "@/components/landing/nav-card";
import { NAV_APPS } from "@/lib/nav-apps";

export const NavCards = () => (
  <section className="mt-8">
    <h2 className="mb-4 text-lg font-bold text-slate-900">Your tools</h2>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {NAV_APPS.map((app) => (
        <NavCard key={app.title} app={app} />
      ))}
    </div>
  </section>
);
