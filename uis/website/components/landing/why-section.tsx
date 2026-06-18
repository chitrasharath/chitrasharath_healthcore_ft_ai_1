"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const whyKeys = ["why1", "why2", "why3", "why4"] as const;

export const WhySection = () => {
  const { t } = useLanguage();

  return (
    <section className="mt-14 grid gap-6 lg:grid-cols-2" aria-labelledby="why-title">
      <article id="why" className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 id="why-title" className="text-2xl font-bold text-slate-900">
          {t("whyTitle")}
        </h2>
        <ul className="mt-4 space-y-3 text-slate-700">
          {whyKeys.map((key) => (
            <li key={key}>{t(key)}</li>
          ))}
        </ul>
      </article>
      <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900">{t("experienceTitle")}</h2>
        <p className="mt-4 leading-7 text-slate-700">{t("experienceBody1")}</p>
        <p className="mt-3 leading-7 text-slate-700">{t("experienceBody2")}</p>
      </article>
    </section>
  );
};
