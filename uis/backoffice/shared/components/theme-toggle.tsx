"use client";

import { useEffect, useState } from "react";

import {
  applyThemeClass,
  persistThemePreference,
  readThemePreference,
  type ThemePreference,
} from "@backoffice/shared/lib/theme";

export const ThemeToggle = () => {
  const [preference, setPreference] = useState<ThemePreference>("system");

  useEffect(() => {
    const initial = readThemePreference();
    setPreference(initial);
    applyThemeClass(initial);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (readThemePreference() === "system") applyThemeClass("system");
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const cycle = () => {
    const order: ThemePreference[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(preference) + 1) % order.length];
    setPreference(next);
    persistThemePreference(next);
  };

  const label =
    preference === "light" ? "Light theme" : preference === "dark" ? "Dark theme" : "System theme";

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${label}. Click to change.`}
      title={label}
      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
    >
      {preference === "light" ? "Light" : preference === "dark" ? "Dark" : "System"}
    </button>
  );
};
