"use client";

import { useLanguage } from "@/lib/i18n/language-context";
import type { Lang } from "@/lib/i18n/translations";

const btnClass = (active: boolean) =>
  `rounded-md border px-3 py-1.5 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 ${
    active
      ? "border-sky-700 bg-sky-50 text-sky-700"
      : "border-slate-300 text-slate-700 hover:border-sky-700 hover:text-sky-700"
  }`;

export const LanguageToggle = () => {
  const { lang, setLang } = useLanguage();
  const langs: Lang[] = ["en", "es"];

  return (
    <div className="flex items-center gap-2" aria-label="Language toggle">
      {langs.map((code) => (
        <button
          key={code}
          type="button"
          className={btnClass(lang === code)}
          aria-pressed={lang === code}
          onClick={() => setLang(code)}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
};
