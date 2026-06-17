const API_FILTER_STORAGE_KEY = "supplier-directory-api-filters";

export const readApiFilterMode = (): boolean => {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(API_FILTER_STORAGE_KEY) === "1";
};

export const writeApiFilterMode = (enabled: boolean): void => {
  sessionStorage.setItem(API_FILTER_STORAGE_KEY, enabled ? "1" : "0");
};
