"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const stats = [
  { value: "12", titleKey: "stat1Title" as const, bodyKey: "stat1Body" as const },
  { value: "200+", titleKey: "stat2Title" as const, bodyKey: "stat2Body" as const },
  { value: "$28M", titleKey: "stat3Title" as const, bodyKey: "stat3Body" as const },
] as const;

export const EvidenceSection = () => {
  const { t } = useLanguage();

  return (
    <section id="evidence" className="mt-14" aria-labelledby="evidence-title">
      <h2 id="evidence-title" className="text-2xl font-bold text-slate-900 sm:text-3xl">
        {t("evidenceTitle")}
      </h2>
      <p className="mt-2 text-slate-600">{t("evidenceIntro")}</p>
      <div className="mt-6 grid gap-5 md:grid-cols-3">
        {stats.map((stat, index) => (
          <article
            key={stat.titleKey}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            aria-labelledby={`stat-${index + 1}-title`}
          >
            <p id={`stat-${index + 1}-title`} className="text-3xl font-extrabold text-sky-800">
              {stat.value}
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{t(stat.titleKey)}</p>
            <p className="mt-1 text-sm text-slate-700">{t(stat.bodyKey)}</p>
          </article>
        ))}
      </div>
      <aside className="mt-5 rounded-lg border border-slate-200 bg-slate-100 p-4" aria-label={t("sourcesTitle")}>
        <h3 className="text-sm font-bold text-slate-900">{t("sourcesTitle")}</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
          <li>{t("source1")}</li>
          <li>{t("source2")}</li>
        </ul>
      </aside>
    </section>
  );
};
