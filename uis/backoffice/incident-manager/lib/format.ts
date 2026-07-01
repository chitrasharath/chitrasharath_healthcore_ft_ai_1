import { DEFAULT_TIMEZONE } from "@backoffice/incident-manager/lib/timezones";

export const parseApiDateTime = (iso: string): Date => {
  if (/[zZ]$/.test(iso) || /[+-]\d{2}:\d{2}$/.test(iso)) {
    return new Date(iso);
  }
  return new Date(`${iso}Z`);
};

export const formatIncidentDate = (iso: string, timeZone: string = DEFAULT_TIMEZONE): string =>
  new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone,
    timeZoneName: "short",
  }).format(parseApiDateTime(iso));
