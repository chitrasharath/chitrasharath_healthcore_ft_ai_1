"use client";

import { useLanguage } from "@/lib/i18n/language-context";

export const SkipLink = () => {
  const { t } = useLanguage();
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-sky-700 focus:px-4 focus:py-2 focus:text-white"
    >
      {t("skip")}
    </a>
  );
};
