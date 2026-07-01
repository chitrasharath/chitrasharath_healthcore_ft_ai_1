export const DEFAULT_TIMEZONE = "America/New_York";

export const TIMEZONE_STORAGE_KEY = "healthcore_inventory_timezone";

/** Inventory routes that display timestamps — timezone control shown on these paths. */
export const INVENTORY_TIME_DISPLAY_PATHS = ["/inventory/orders"] as const;

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

export const showsInventoryTime = (pathname: string): boolean =>
  INVENTORY_TIME_DISPLAY_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
