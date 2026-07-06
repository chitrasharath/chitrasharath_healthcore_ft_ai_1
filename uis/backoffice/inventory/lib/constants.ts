export const CLINICS: { id: number; name: string }[] = [
  { id: 1, name: "HealthCore Austin Central" },
  { id: 2, name: "HealthCore Austin North" },
  { id: 3, name: "HealthCore San Antonio" },
  { id: 4, name: "HealthCore Miami" },
  { id: 5, name: "HealthCore Orlando" },
  { id: 6, name: "HealthCore Atlanta" },
];

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
