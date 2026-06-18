import type { FormErrorKey, Lang } from "@/lib/i18n/translations";
import { formErrors } from "@/lib/i18n/translations";
import { clinicClosingHour } from "@/lib/clinics";

export type EnquiryFormValues = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email: string;
  phone: string;
  preferred_language: string;
  preferred_clinic: string;
  preferred_date: string;
  preferred_time: string;
  service_type: string;
  new_patient: string;
  has_insurance: string;
  insurance_provider: string;
  insurance_member_id: string;
  patient_id: string;
  health_concern: string;
  contact_consent: boolean;
};

export type FieldErrors = Partial<Record<keyof EnquiryFormValues | "paediatric", string>>;

const parseDate = (value: string): Date | null => {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
};

const normalizeToday = (): Date => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
};

export const calcAge = (dob: Date): number => {
  const today = normalizeToday();
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) age -= 1;
  return age;
};

const getNextBusinessDay = (fromDate: Date): Date => {
  const date = new Date(fromDate);
  date.setDate(date.getDate() + 1);
  while (date.getDay() === 0 || date.getDay() === 6) date.setDate(date.getDate() + 1);
  date.setHours(0, 0, 0, 0);
  return date;
};

const getMaxPreferredDate = (fromDate: Date): Date => {
  const max = new Date(fromDate);
  max.setDate(max.getDate() + 60);
  max.setHours(0, 0, 0, 0);
  return max;
};

const nameIsValid = (value: string): boolean =>
  /^[A-Za-zÀ-ÖØ-öø-ÿ]{2,50}$/.test(value.trim());

const err = (lang: Lang, key: FormErrorKey): string => formErrors(lang, key);

export const validateNameField = (lang: Lang, value: string, field: "first_name" | "last_name"): string | null =>
  nameIsValid(value) ? null : err(lang, field);

export const validateDob = (lang: Lang, value: string): string | null => {
  const dob = parseDate(value);
  const today = normalizeToday();
  if (!dob) return err(lang, "date_of_birth");
  const age = calcAge(dob);
  if (dob > today || age < 0 || age > 120) return err(lang, "date_of_birth");
  return null;
};

export const validateEmail = (lang: Lang, value: string): string | null =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) ? null : err(lang, "email");

export const validatePhone = (lang: Lang, value: string): string | null =>
  /^\+\d{1,3}[\d\s-]{6,20}$/.test(value.trim()) ? null : err(lang, "phone");

export const validateRequiredSelect = (lang: Lang, value: string, field: FormErrorKey): string | null =>
  value ? null : err(lang, field);

export const validatePreferredDate = (lang: Lang, value: string): string | null => {
  const selected = parseDate(value);
  const today = normalizeToday();
  const minDate = getNextBusinessDay(today);
  const maxDate = getMaxPreferredDate(today);
  if (!selected || selected < minDate || selected > maxDate) return err(lang, "preferred_date");
  return null;
};

export const validateService = (lang: Lang, service: string, dobValue: string): string | null => {
  if (!service) return err(lang, "service_type");
  if (service === "Paediatric Care") {
    const dob = parseDate(dobValue);
    if (!dob || calcAge(dob) >= 18) return err(lang, "paediatric");
  }
  return null;
};

export const validateInsuranceProvider = (lang: Lang, hasInsurance: string, value: string): string | null => {
  if (hasInsurance !== "Yes") return null;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > 100) return err(lang, "insurance_provider");
  return null;
};

export const validateMemberId = (lang: Lang, hasInsurance: string, value: string): string | null => {
  if (hasInsurance !== "Yes") return null;
  if (!/^[A-Za-z0-9]{6,20}$/.test(value.trim())) return err(lang, "insurance_member_id");
  return null;
};

export const validatePatientId = (lang: Lang, newPatient: string, value: string): string | null => {
  if (newPatient !== "No" || value.trim().length === 0) return null;
  if (!/^HC-[A-Za-z0-9]{6}$/.test(value.trim())) return err(lang, "patient_id");
  return null;
};

export const validateHealthConcern = (
  lang: Lang,
  value: string,
  t: (key: "healthConcernBase" | "healthConcernRemaining") => string
): string | null => {
  const length = value.trim().length;
  if (length < 20 || length > 500) {
    const remaining = Math.max(0, 20 - length);
    return `${t("healthConcernBase")} (${remaining} ${t("healthConcernRemaining")})`;
  }
  return null;
};

export const validateConsent = (lang: Lang, checked: boolean): string | null =>
  checked ? null : err(lang, "contact_consent");

export const shouldShowEveningWarning = (clinic: string, time: string): boolean =>
  time === "Evening (5pm-8pm)" && Boolean(clinic) && (clinicClosingHour[clinic] ?? 20) < 20;

export const emptyFormValues = (): EnquiryFormValues => ({
  first_name: "",
  last_name: "",
  date_of_birth: "",
  email: "",
  phone: "",
  preferred_language: "",
  preferred_clinic: "",
  preferred_date: "",
  preferred_time: "",
  service_type: "",
  new_patient: "",
  has_insurance: "",
  insurance_provider: "",
  insurance_member_id: "",
  patient_id: "",
  health_concern: "",
  contact_consent: false,
});
