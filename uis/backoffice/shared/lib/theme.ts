export type ThemePreference = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "healthcore_theme";

export const readThemePreference = (): ThemePreference => {
  if (typeof window === "undefined") return "system";
  const raw = localStorage.getItem(THEME_STORAGE_KEY);
  if (raw === "light" || raw === "dark" || raw === "system") return raw;
  return "system";
};

export const resolveTheme = (preference: ThemePreference): "light" | "dark" => {
  if (preference === "light" || preference === "dark") return preference;
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

export const applyThemeClass = (preference: ThemePreference): void => {
  if (typeof document === "undefined") return;
  const resolved = resolveTheme(preference);
  document.documentElement.classList.toggle("dark", resolved === "dark");
};

export const persistThemePreference = (preference: ThemePreference): void => {
  localStorage.setItem(THEME_STORAGE_KEY, preference);
  applyThemeClass(preference);
};
