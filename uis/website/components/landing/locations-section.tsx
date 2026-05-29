"use client";

import { US_CLINICS } from "@/lib/clinics";
import { useLanguage } from "@/lib/i18n/language-context";

export const LocationsSection = () => {
  const { t } = useLanguage();

  return (
    <section id="locations" className="mt-14" aria-labelledby="locations-title">
      <h2 id="locations-title" className="text-2xl font-bold text-slate-900 sm:text-3xl">
        {t("locationsTitle")}
      </h2>
      <p className="mt-2 text-slate-600">{t("locationsIntro")}</p>

      <div className="mt-6 hidden overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm md:block">
        <table className="min-w-full border-collapse text-left">
          <caption className="sr-only">{t("locationsCaption")}</caption>
          <thead className="bg-slate-100 text-sm uppercase tracking-wide text-slate-700">
            <tr>
              <th scope="col" className="px-4 py-3">{t("thClinic")}</th>
              <th scope="col" className="px-4 py-3">{t("thCity")}</th>
              <th scope="col" className="px-4 py-3">{t("thState")}</th>
              <th scope="col" className="px-4 py-3">{t("thPhone")}</th>
              <th scope="col" className="px-4 py-3">{t("thHours")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-sm text-slate-700">
            {US_CLINICS.map((clinic) => (
              <tr key={clinic.name}>
                <td className="px-4 py-3">{clinic.name}</td>
                <td className="px-4 py-3">{clinic.city}</td>
                <td className="px-4 py-3">{clinic.state}</td>
                <td className="px-4 py-3">{clinic.phone}</td>
                <td className="px-4 py-3">{t(clinic.hoursKey)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid gap-4 md:hidden">
        {US_CLINICS.map((clinic) => (
          <article key={clinic.name} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-bold text-sky-800">{clinic.name}</h3>
            <p className="text-sm text-slate-700">
              {clinic.city}, {clinic.state}
            </p>
            <p className="text-sm text-slate-700">{clinic.phone}</p>
            <p className="text-sm text-slate-600">{t(clinic.hoursKey)}</p>
          </article>
        ))}
      </div>
    </section>
  );
};
