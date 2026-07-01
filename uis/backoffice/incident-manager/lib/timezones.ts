export const DEFAULT_TIMEZONE = "America/New_York";

export const TIMEZONE_STORAGE_KEY = "healthcore_incident_manager_timezone";

export type TimezoneOption = {
  value: string;
  label: string;
};

export const DISPLAY_TIMEZONES: TimezoneOption[] = [
  { value: "America/New_York", label: "Eastern Time (ET)" },
  { value: "America/Chicago", label: "Central Time (CT)" },
  { value: "America/Denver", label: "Mountain Time (MT)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
  { value: "America/Anchorage", label: "Alaska Time (AKT)" },
  { value: "Pacific/Honolulu", label: "Hawaii Time (HT)" },
  { value: "Europe/London", label: "UK Time (GMT/BST)" },
  { value: "UTC", label: "UTC" },
];

export const isValidTimezone = (value: string): boolean =>
  DISPLAY_TIMEZONES.some((tz) => tz.value === value);

export const showsIncidentTime = (pathname: string): boolean => {
  if (pathname === "/incident-manager/list") return true;
  return /^\/incident-manager\/\d+(\/edit)?$/.test(pathname);
};
