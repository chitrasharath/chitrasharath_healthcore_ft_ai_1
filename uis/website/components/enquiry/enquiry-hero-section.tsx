"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const FORM_IMAGE =
  "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=1200&q=80";

export const EnquiryHeroSection = () => {
  const { t } = useLanguage();

  return (
    <section className="grid gap-8 rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 px-6 py-10 text-white shadow-xl lg:grid-cols-2 lg:items-center lg:px-10">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("formTitle")}</h1>
        <p className="mt-4 text-base leading-7 text-sky-100">{t("formIntro")}</p>
        <p className="mt-4 rounded-md border border-sky-200 bg-white px-4 py-3 text-sm font-semibold text-sky-900 shadow-sm">
          {t("partnerNote")}
        </p>
      </div>
      <figure>
        <img
          src={FORM_IMAGE}
          alt="A healthcare specialist using a tablet while discussing care options"
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
