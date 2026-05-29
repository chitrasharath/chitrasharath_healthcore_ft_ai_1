"use client";

import { useLanguage } from "@/lib/i18n/language-context";

export const AuthorSection = () => {
  const { t } = useLanguage();

  return (
    <section
      className="mt-8 rounded-xl border border-slate-200 bg-slate-100 p-4"
      aria-label={t("authorSectionAria")}
    >
      <p className="text-sm font-semibold text-slate-800">{t("authorByline")}</p>
      <p className="mt-1 text-sm text-slate-700">{t("reviewDate")}</p>
    </section>
  );
};
