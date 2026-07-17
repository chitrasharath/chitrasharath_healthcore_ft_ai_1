export type Clinic = {
  id: number;
  name: string;
  jurisdiction: "us" | "uk";
};

/** Clinic catalog — jurisdiction is clinic location, not supply country. */
export const CLINICS: Clinic[] = [
  { id: 1, name: "HealthCore Austin Central", jurisdiction: "us" },
  { id: 2, name: "HealthCore Austin North", jurisdiction: "us" },
  { id: 3, name: "HealthCore San Antonio", jurisdiction: "us" },
  { id: 4, name: "HealthCore Miami", jurisdiction: "us" },
  { id: 5, name: "HealthCore Orlando", jurisdiction: "us" },
  { id: 6, name: "HealthCore Atlanta", jurisdiction: "us" },
  { id: 7, name: "HealthCore London Canary Wharf", jurisdiction: "uk" },
  { id: 8, name: "HealthCore London Kensington", jurisdiction: "uk" },
  { id: 9, name: "HealthCore Manchester", jurisdiction: "uk" },
];

export const clinicJurisdiction = (clinicId: number): "us" | "uk" | null =>
  CLINICS.find((clinic) => clinic.id === clinicId)?.jurisdiction ?? null;

export const VENDORS = [
  "MedLine Industries",
  "Cardinal Health UK",
  "Bound Tree Medical",
];

export const CONSUMPTION_TYPES: { value: string; label: string }[] = [
  { value: "clinical_use", label: "Clinical Use" },
  { value: "expiry_waste", label: "Expiry / Waste" },
];

export const CATEGORY_LABELS: Record<string, string> = {
  ppe: "PPE",
  wound_care: "Wound Care",
  diagnostics: "Diagnostics",
  medications: "Medications",
  consumables: "Consumables",
};
