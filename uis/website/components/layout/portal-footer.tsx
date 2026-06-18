"use client";

import { useLanguage } from "@/lib/i18n/language-context";

const social = [
  { label: "LinkedIn", href: "https://linkedin.com/company/healthcore" },
  { label: "Facebook", href: "https://facebook.com/healthcore" },
  { label: "Instagram", href: "https://instagram.com/healthcore" },
];

export const PortalFooter = () => {
  const { t } = useLanguage();

  return (
    <footer className="mt-14 border-t border-slate-200 bg-white" role="contentinfo">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 text-sm text-slate-600 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <p>{t("footerCopyright")}</p>
        <nav aria-label="Social media">
          <ul className="flex items-center gap-4">
            {social.map((item) => (
              <li key={item.label}>
                <a
                  href={item.href}
                  className="underline hover:text-sky-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
};
