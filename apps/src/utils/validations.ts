import { Claim, Clinician, ClinicianRole } from "../types/models.js";

const VALID_CLINICIAN_ROLES: Set<ClinicianRole> = new Set<ClinicianRole>([
  "physician",
  "nurse_practitioner",
  "nurse",
  "medical_assistant",
]);

function isValidDateString(value: string): boolean {
  if (typeof value !== "string" || value.trim() === "") {
    return false;
  }

  const parsedDate: Date = new Date(value);
  return !Number.isNaN(parsedDate.getTime());
}

function isFutureDate(value: string): boolean {
  const parsedDate: Date = new Date(value);
  const now: Date = new Date();
  return parsedDate.getTime() > now.getTime();
}

export function validateClaim(
  claim: Claim,
  knownLocationIds: string[]
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!(claim.claimAmount > 0)) {
    errors.push("claimAmount must be greater than 0.");
  }

  if (!isValidDateString(claim.submissionDate)) {
    errors.push("submissionDate must be a valid ISO 8601 date string.");
  } else if (isFutureDate(claim.submissionDate)) {
    errors.push("submissionDate must not be a future date.");
  }

  if (!knownLocationIds.includes(claim.locationId)) {
    errors.push("locationId must match a known clinic ID.");
  }

  if (claim.status === "denied" && !claim.denialReason) {
    errors.push("denialReason is required when status is denied.");
  }

  const patientIdPattern: RegExp = /^HC-[A-Za-z0-9]{6}$/;
  if (!patientIdPattern.test(claim.patientId)) {
    errors.push("patientId must match format HC- followed by 6 alphanumeric characters.");
  }

  return { valid: errors.length === 0, errors };
}

export function validateClinician(clinician: Clinician): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (clinician.cmeHoursRequired < 0) {
    errors.push("cmeHoursRequired must be greater than or equal to 0.");
  }

  if (clinician.cmeHoursLogged < 0) {
    errors.push("cmeHoursLogged must be greater than or equal to 0.");
  }

  if (!isValidDateString(clinician.licenceExpiryDate)) {
    errors.push("licenceExpiryDate must be a valid ISO 8601 date string.");
  } else {
    const today: Date = new Date();
    const expiryDate: Date = new Date(clinician.licenceExpiryDate);

    if (expiryDate.getTime() < today.getTime()) {
      errors.push("licenceExpiryDate is expired and must be present or future date.");
    }
  }

  if (!VALID_CLINICIAN_ROLES.has(clinician.role)) {
    errors.push("role must be one of physician, nurse_practitioner, nurse, medical_assistant.");
  }

  return { valid: errors.length === 0, errors };
}

export function isDenialRateAboveThreshold(rate: number, threshold: number = 8): boolean {
  return rate > threshold;
}

export function isNoShowRateAboveThreshold(rate: number, threshold: number = 20): boolean {
  return rate > threshold;
}
