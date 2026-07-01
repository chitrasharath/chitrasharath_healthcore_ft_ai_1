import { CATEGORY_LABELS, CLINICS, CONSUMPTION_TYPES } from "@backoffice/inventory/lib/constants";

export const formatClinicName = (clinicId: number): string => {
  const clinic = CLINICS.find((c) => c.id === clinicId);
  return clinic ? clinic.name : `Unknown clinic (${clinicId})`;
};

/** API stores UTC; naive ISO strings (no offset) must not be parsed as local time. */
export const parseApiDateTime = (iso: string): Date => {
  if (/[zZ]$/.test(iso) || /[+-]\d{2}:\d{2}$/.test(iso)) {
    return new Date(iso);
  }
  return new Date(`${iso}Z`);
};

export const formatOrderDate = (iso: string, timeZone: string): string =>
  new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone,
    timeZoneName: "short",
  }).format(parseApiDateTime(iso));

export const formatConsumptionType = (value: string | null): string => {
  if (!value) return "—";
  return CONSUMPTION_TYPES.find((t) => t.value === value)?.label ?? value;
};

export const formatCategoryLabel = (category: string): string =>
  CATEGORY_LABELS[category] ?? category;
