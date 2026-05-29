"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const services = [
  {
    titleKey: "service1Title" as const,
    points: ["service1Point1", "service1Point2"] as const,
  },
  {
    titleKey: "service2Title" as const,
    points: ["service2Point1", "service2Point2"] as const,
  },
  {
    titleKey: "service3Title" as const,
    points: ["service3Point1", "service3Point2"] as const,
  },
];

export const ServicesSection = () => {
  const { t } = useLanguage();

  return (
    <section id="services" className="mt-14" aria-labelledby="services-title">
      <div className="mb-6">
        <h2 id="services-title" className="text-2xl font-bold text-slate-900 sm:text-3xl">
          {t("servicesTitle")}
        </h2>
        <p className="mt-2 text-slate-600">{t("servicesIntro")}</p>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        {services.map((service) => (
          <article
            key={service.titleKey}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h3 className="text-lg font-bold text-sky-800">{t(service.titleKey)}</h3>
            <ul className="mt-3 space-y-2 text-slate-700">
              {service.points.map((pointKey) => (
                <li key={pointKey}>{t(pointKey)}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
};
