/** @jest-environment node */

import {
  resolveTheme,
  THEME_STORAGE_KEY,
  type ThemePreference,
} from "@backoffice/shared/lib/theme";

describe("theme helpers", () => {
  it("resolves explicit preferences", () => {
    expect(resolveTheme("light")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
  });

  it("uses storage key constant", () => {
    expect(THEME_STORAGE_KEY).toBe("healthcore_theme");
    const prefs: ThemePreference[] = ["light", "dark", "system"];
    expect(prefs).toHaveLength(3);
  });
});
