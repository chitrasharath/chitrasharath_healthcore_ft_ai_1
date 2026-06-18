"use client";

import Link from "next/link";

import { HealthcoreLogo } from "@/components/layout/healthcore-logo";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { useLanguage } from "@/lib/i18n/language-context";

type NavItem = { href: string; key: "navHome" | "navServices" | "navLocations" | "navContact" };

const navItems: NavItem[] = [
  { href: "/#home", key: "navHome" },
  { href: "/#services", key: "navServices" },
  { href: "/#locations", key: "navLocations" },
  { href: "/#contact", key: "navContact" },
];

const linkClass =
  "rounded-md px-3 py-2 text-slate-700 transition hover:bg-sky-50 hover:text-sky-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700";

export const PortalHeader = ({ onLanding = true }: { onLanding?: boolean }) => {
  const { t } = useLanguage();
  const homeHref = onLanding ? "#home" : "/#home";

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur" role="banner">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <Link href={homeHref} className="inline-flex items-center gap-2 text-2xl font-bold tracking-tight text-sky-800" aria-label="HealthCore Home">
          <HealthcoreLogo />
          <span>HealthCore</span>
        </Link>

        <nav aria-label="Primary" className="order-3 w-full md:order-2 md:w-auto">
          <ul className="flex flex-wrap items-center gap-2 text-sm font-semibold sm:gap-3 md:text-base">
            {navItems.map((item) => (
              <li key={item.key}>
                <Link
                  href={onLanding ? item.href.replace("/#", "#") : item.href}
                  className={linkClass}
                >
                  {t(item.key)}
                </Link>
              </li>
            ))}
            <li>
              <Link href="/enquiry-form" className="rounded-md bg-sky-700 px-3 py-2 text-white transition hover:bg-sky-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700">
                {t("navApply")}
              </Link>
            </li>
          </ul>
        </nav>

        <div className="order-2 md:order-3">
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
};
