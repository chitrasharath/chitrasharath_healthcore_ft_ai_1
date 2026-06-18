export const VALID_CATEGORIES = [
  "medical_supplies",
  "laboratory_services",
  "pharmaceutical",
  "clinical_software",
  "it_infrastructure",
  "hr_and_payroll_software",
  "cleaning_and_facilities",
  "patient_communication",
  "billing_and_coding_software",
  "training_platforms",
] as const;

export type Category = (typeof VALID_CATEGORIES)[number];

export const CATEGORY_LABELS: Record<Category, string> = {
  medical_supplies: "Medical Supplies",
  laboratory_services: "Laboratory Services",
  pharmaceutical: "Pharmaceutical",
  clinical_software: "Clinical Software",
  it_infrastructure: "IT Infrastructure",
  hr_and_payroll_software: "HR and Payroll Software",
  cleaning_and_facilities: "Cleaning and Facilities",
  patient_communication: "Patient Communication",
  billing_and_coding_software: "Billing and Coding Software",
  training_platforms: "Training Platforms",
};

export const COMPLIANCE_PROMPT_CATEGORIES: Category[] = [
  "clinical_software",
  "it_infrastructure",
  "patient_communication",
  "billing_and_coding_software",
];

export const currencyForCountry = (country: "USA" | "UK"): "USD" | "GBP" =>
  country === "USA" ? "USD" : "GBP";

export const formatCategoryLabels = (categories: string[]): string =>
  categories.map((c) => CATEGORY_LABELS[c as Category] ?? c).join(", ");
