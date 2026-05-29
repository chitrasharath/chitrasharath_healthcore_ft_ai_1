"use client";

import Link from "next/link";

import { useLanguage } from "@/lib/i18n/language-context";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?auto=format&fit=crop&w=1200&q=80";

export const HeroSection = () => {
  const { t } = useLanguage();

  return (
    <section
      id="home"
      className="grid gap-8 rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 px-6 py-10 text-white shadow-xl lg:grid-cols-2 lg:items-center lg:px-10"
    >
      <div>
        <p className="mb-3 inline-flex rounded-full bg-white/15 px-3 py-1 text-sm font-semibold">
          {t("heroKicker")}
        </p>
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("heroTitle")}</h1>
        <p className="mt-4 text-base leading-7 text-sky-100 sm:text-lg">{t("heroSubtitle")}</p>
        <Link
          href="/enquiry-form"
          className="mt-6 inline-flex rounded-md bg-white px-5 py-3 text-sm font-bold text-sky-800 shadow-md transition hover:bg-sky-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        >
          {t("heroCta")}
        </Link>
      </div>
      <figure>
        <img
          src={HERO_IMAGE}
          alt={t("heroImageAlt")}
          className="h-72 w-full rounded-xl object-cover shadow-lg sm:h-80"
          loading="eager"
          fetchPriority="high"
          width={1200}
          height={800}
        />
      </figure>
    </section>
  );
};
