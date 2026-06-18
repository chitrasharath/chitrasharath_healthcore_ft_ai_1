import type { UiTranslationKey } from "@/lib/i18n/translations";

export const TIME_OPTIONS: { value: string; key: UiTranslationKey }[] = [
  { value: "Morning (7am-12pm)", key: "timeMorning" },
  { value: "Afternoon (12pm-5pm)", key: "timeAfternoon" },
  { value: "Evening (5pm-8pm)", key: "timeEvening" },
];

export const SERVICE_OPTIONS: { value: string; key: UiTranslationKey }[] = [
  { value: "Primary Care", key: "servicePrimary" },
  { value: "Chronic Disease Management", key: "serviceChronic" },
  { value: "Specialist Consultation", key: "serviceSpecialist" },
  { value: "Preventive Health", key: "servicePreventive" },
  { value: "Women's Health", key: "serviceWomens" },
  { value: "Paediatric Care", key: "servicePaediatric" },
  { value: "Mental Health", key: "serviceMental" },
];
