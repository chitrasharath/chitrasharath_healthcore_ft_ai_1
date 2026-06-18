"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const CONTACT_IMAGE =
  "https://images.pexels.com/photos/6129688/pexels-photo-6129688.jpeg?auto=compress&cs=tinysrgb&w=1200";

export const ContactSection = () => {
  const { t } = useLanguage();

  return (
    <section
      id="contact"
      className="mt-14 grid gap-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:grid-cols-2 lg:items-center"
    >
      <div>
        <h2 className="text-2xl font-bold text-slate-900">{t("contactTitle")}</h2>
        <ul className="mt-4 space-y-2 text-slate-700">
          <li>
            <span className="font-semibold">{t("contactGeneral")}</span>{" "}
            <a href="mailto:info@healthcore.com" className="text-sky-700 underline">
              info@healthcore.com
            </a>
          </li>
          <li>
            <span className="font-semibold">{t("contactAustin")}</span> (512) 340-8800
          </li>
          <li>
            <span className="font-semibold">{t("contactMiami")}</span> (305) 510-7700
          </li>
          <li>
            <span className="font-semibold">{t("contactUk")}</span> +44 20 7946 0100
          </li>
        </ul>
      </div>
      <figure>
        <img
          src={CONTACT_IMAGE}
          alt={t("contactImageAlt")}
          className="h-64 w-full rounded-xl object-cover"
          loading="lazy"
          width={1200}
          height={800}
        />
      </figure>
    </section>
  );
};
