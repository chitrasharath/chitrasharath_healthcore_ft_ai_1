"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  STORAGE_KEY,
  translate,
  type Lang,
  type TranslationKey,
  type UiTranslationKey,
} from "@/lib/i18n/translations";

type LanguageContextValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: UiTranslationKey) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

const getInitialLang = (param: string | null): Lang => {
  if (param === "en" || param === "es") return param;
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "es") return stored;
  }
  return "en";
};

export const LanguageProvider = ({ children }: { children: ReactNode }) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramLang = searchParams.get("lang");
  const [storedLang, setStoredLang] = useState<Lang>(() => getInitialLang(paramLang));
  const lang: Lang = paramLang === "en" || paramLang === "es" ? paramLang : storedLang;

  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem(STORAGE_KEY, lang);
  }, [lang]);

  const setLang = useCallback(
    (next: Lang) => {
      setStoredLang(next);
      const params = new URLSearchParams(searchParams.toString());
      params.set("lang", next);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const t = useCallback((key: UiTranslationKey) => translate(lang, key), [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = (): LanguageContextValue => {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
};

export type { Lang, TranslationKey };
