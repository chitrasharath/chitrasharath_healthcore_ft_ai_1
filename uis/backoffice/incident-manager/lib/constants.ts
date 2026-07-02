export const BRANCHES = [
  { value: "US-TX-01", label: "US-TX-01 — Austin, TX Main" },
  { value: "US-TX-02", label: "US-TX-02 — Austin, TX North" },
  { value: "US-TX-03", label: "US-TX-03 — Houston, TX" },
  { value: "US-FL-01", label: "US-FL-01 — Miami, FL" },
  { value: "US-FL-02", label: "US-FL-02 — Orlando, FL" },
  { value: "US-FL-03", label: "US-FL-03 — Tampa, FL" },
  { value: "US-GA-01", label: "US-GA-01 — Atlanta Midtown" },
  { value: "US-GA-02", label: "US-GA-02 — Atlanta Buckhead" },
  { value: "US-GA-03", label: "US-GA-03 — Savannah, GA" },
  { value: "UK-LON-01", label: "UK-LON-01 — London Canary Wharf" },
  { value: "UK-LON-02", label: "UK-LON-02 — London Kensington" },
  { value: "UK-MAN-01", label: "UK-MAN-01 — Manchester" },
  { value: "Central", label: "Central — HQ / not branch-specific" },
] as const;

export const CATEGORIES = [
  { value: "APPOINTMENT", label: "Appointment" },
  { value: "BILLING", label: "Billing" },
  { value: "CLINICAL_CARE", label: "Clinical Care" },
  { value: "ACCESSIBILITY", label: "Accessibility" },
  { value: "ADMINISTRATIVE", label: "Administrative" },
] as const;

export const ORIGINS = [
  { value: "customer", label: "Customer" },
  { value: "branch", label: "Branch" },
  { value: "internal", label: "Internal" },
] as const;

export const STATUSES = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In Progress" },
  { value: "resolved", label: "Resolved" },
  { value: "discarded", label: "Discarded" },
] as const;

export const STATUS_TRANSITIONS: Record<string, string[]> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],
  discarded: [],
};

export const STATUS_BADGE_CLASSES: Record<string, string> = {
  open: "rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800",
  in_progress: "rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800",
  resolved: "rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800",
  discarded: "rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800",
};
