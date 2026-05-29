"use client";

import { useLanguage } from "@/lib/i18n/language-context";

type EveningWarningProps = { visible: boolean };

export const EveningWarning = ({ visible }: EveningWarningProps) => {
  const { t } = useLanguage();
  if (!visible) return null;

  return (
    <div
      className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900"
      role="status"
      aria-live="polite"
    >
      {t("warningEvening")}
    </div>
  );
};
