export type ClinicRow = {
  name: string;
  city: string;
  state: string;
  phone: string;
  hoursKey: "locHours1" | "locHours2" | "locHours3" | "locHours4" | "locHours5" | "locHours6";
};

export const US_CLINICS: ClinicRow[] = [
  { name: "HealthCore Austin Central", city: "Austin", state: "TX", phone: "(512) 340-8800", hoursKey: "locHours1" },
  { name: "HealthCore Austin North", city: "Austin", state: "TX", phone: "(512) 340-8810", hoursKey: "locHours2" },
  { name: "HealthCore San Antonio", city: "San Antonio", state: "TX", phone: "(210) 720-4400", hoursKey: "locHours3" },
  { name: "HealthCore Miami", city: "Miami", state: "FL", phone: "(305) 510-7700", hoursKey: "locHours4" },
  { name: "HealthCore Orlando", city: "Orlando", state: "FL", phone: "(407) 892-6600", hoursKey: "locHours5" },
  { name: "HealthCore Atlanta", city: "Atlanta", state: "GA", phone: "(404) 330-9900", hoursKey: "locHours6" },
];

export const clinicClosingHour: Record<string, number> = {
  "HealthCore Austin Central": 20,
  "HealthCore Austin North": 19,
  "HealthCore San Antonio": 18,
  "HealthCore Miami": 20,
  "HealthCore Orlando": 18,
  "HealthCore Atlanta": 19,
};
