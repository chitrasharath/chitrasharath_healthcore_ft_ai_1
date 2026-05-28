import { Claim, Clinician } from "../types/models.js";

export function findClaimById(claims: Claim[], claimId: string): Claim | null {
  for (const claim of claims) {
    if (claim.claimId === claimId) {
      return claim;
    }
  }

  return null;
}

export function findClinicianById(clinicians: Clinician[], clinicianId: string): Clinician | null {
  for (const clinician of clinicians) {
    if (clinician.clinicianId === clinicianId) {
      return clinician;
    }
  }

  return null;
}

export function binarySearchClaimById(sortedClaims: Claim[], targetId: string): number {
  let left: number = 0;
  let right: number = sortedClaims.length - 1;

  while (left <= right) {
    const middle: number = Math.floor((left + right) / 2);
    const currentId: string = sortedClaims[middle].claimId;

    if (currentId === targetId) {
      return middle;
    }

    if (currentId < targetId) {
      left = middle + 1;
    } else {
      right = middle - 1;
    }
  }

  return -1;
}
