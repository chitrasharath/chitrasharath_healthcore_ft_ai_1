"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const faqs = [
  { q: "faqQ1", a: "faqA1" },
  { q: "faqQ2", a: "faqA2" },
  { q: "faqQ3", a: "faqA3" },
] as const;

export const FaqSection = () => {
  const { t } = useLanguage();

  return (
    <section
      id="faq"
      className="mt-14 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-labelledby="faq-title"
    >
      <h2 id="faq-title" className="text-2xl font-bold text-slate-900">
        {t("faqTitle")}
      </h2>
      <p className="mt-2 text-slate-600">{t("faqIntro")}</p>
      <div className="mt-5 space-y-3">
        {faqs.map((faq) => (
          <details key={faq.q} className="rounded-md border border-slate-200 p-4">
            <summary className="cursor-pointer font-semibold text-slate-900">{t(faq.q)}</summary>
            <p className="mt-2 text-slate-700">{t(faq.a)}</p>
          </details>
        ))}
      </div>
    </section>
  );
};
