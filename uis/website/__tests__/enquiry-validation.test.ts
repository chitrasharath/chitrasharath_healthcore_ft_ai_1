import {
  calcAge,
  shouldShowEveningWarning,
  validateConsent,
  validateDob,
  validateEmail,
  validateHealthConcern,
  validateInsuranceProvider,
  validateMemberId,
  validateNameField,
  validatePatientId,
  validatePhone,
  validatePreferredDate,
  validateService,
} from "@/lib/enquiry-validation";

const FROZEN_NOW = new Date("2025-06-24T12:00:00Z");

const formatDate = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const addDays = (from: Date, days: number): Date => {
  const next = new Date(from);
  next.setDate(next.getDate() + days);
  return next;
};

const healthConcernT = (key: "healthConcernBase" | "healthConcernRemaining"): string =>
  key === "healthConcernBase" ? "Please describe your concern" : "characters remaining";

describe("enquiry-validation", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(FROZEN_NOW);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test("validateNameField — valid name returns null", () => {
    expect(validateNameField("en", "Alice", "first_name")).toBeNull();
  });

  test("validateNameField — empty string returns error", () => {
    expect(validateNameField("en", "", "first_name")).not.toBeNull();
  });

  test("validateNameField — name with digits returns error", () => {
    expect(validateNameField("en", "Alice123", "first_name")).not.toBeNull();
  });

  test("validateDob — valid adult dob returns null", () => {
    expect(validateDob("en", "2000-06-24")).toBeNull();
  });

  test("validateDob — future date returns error", () => {
    expect(validateDob("en", formatDate(addDays(FROZEN_NOW, 1)))).not.toBeNull();
  });

  test("validateDob — age over 120 returns error", () => {
    expect(validateDob("en", "1850-01-01")).not.toBeNull();
  });

  test("validateEmail — valid email returns null", () => {
    expect(validateEmail("en", "a@b.com")).toBeNull();
  });

  test("validateEmail — missing @ returns error", () => {
    expect(validateEmail("en", "invalid")).not.toBeNull();
  });

  test("validatePhone — valid intl phone returns null", () => {
    expect(validatePhone("en", "+1 555-123-4567")).toBeNull();
  });

  test("validatePhone — no country code returns error", () => {
    expect(validatePhone("en", "5551234567")).not.toBeNull();
  });

  test("validatePreferredDate — next business day returns null", () => {
    expect(validatePreferredDate("en", "2025-06-25")).toBeNull();
  });

  // BUG-001: weekend rejection not implemented yet — see TESTING.md
  test.failing("validatePreferredDate — weekend returns error", () => {
    expect(validatePreferredDate("en", "2025-06-28")).not.toBeNull();
  });

  test("validatePreferredDate — date > 60 days out returns error", () => {
    expect(validatePreferredDate("en", "2025-08-24")).not.toBeNull();
  });

  test('validateService — Paediatric Care for adult returns error', () => {
    expect(validateService("en", "Paediatric Care", "2000-06-24")).not.toBeNull();
  });

  test("validateInsuranceProvider — has insurance but empty provider returns error", () => {
    expect(validateInsuranceProvider("en", "Yes", "")).not.toBeNull();
  });

  test("validateMemberId — invalid format returns error", () => {
    expect(validateMemberId("en", "Yes", "!!!")).not.toBeNull();
  });

  test("validatePatientId — existing patient with invalid format returns error", () => {
    expect(validatePatientId("en", "No", "INVALID")).not.toBeNull();
  });

  test("validatePatientId — valid HC- format returns null", () => {
    expect(validatePatientId("en", "No", "HC-ABC123")).toBeNull();
  });

  test("validateHealthConcern — too short returns error with remaining count", () => {
    const error = validateHealthConcern("en", "short", healthConcernT);
    expect(error).not.toBeNull();
    expect(error).toContain("15");
  });

  test("validateConsent — false returns error", () => {
    expect(validateConsent("en", false)).not.toBeNull();
  });

  test("shouldShowEveningWarning — evening + early-close clinic returns true", () => {
    expect(shouldShowEveningWarning("HealthCore San Antonio", "Evening (5pm-8pm)")).toBe(true);
  });

  test("calcAge — birthday today", () => {
    const today = new Date(FROZEN_NOW);
    today.setHours(0, 0, 0, 0);
    expect(calcAge(today)).toBe(0);
  });
});
