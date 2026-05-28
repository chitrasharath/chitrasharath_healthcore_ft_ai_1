import {
  Appointment,
  Claim,
  Clinician,
  CMEReport,
  CMEStatus,
  Location,
  ServiceType,
} from "../types/models.js";
import { groupClaimsBy } from "./collections.js";

function roundTo(value: number, decimals: number): number {
  const factor: number = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function percentage(part: number, total: number, decimals: number = 2): number {
  if (total === 0) {
    return 0;
  }

  return roundTo((part / total) * 100, decimals);
}

function parseDate(dateInput: string): Date | null {
  const date: Date = new Date(dateInput);
  return Number.isNaN(date.getTime()) ? null : date;
}

function toUtcDateOnly(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function diffCalendarDays(start: Date, end: Date): number {
  const utcStart: Date = toUtcDateOnly(start);
  const utcEnd: Date = toUtcDateOnly(end);
  const dayMs: number = 24 * 60 * 60 * 1000;
  return Math.round((utcEnd.getTime() - utcStart.getTime()) / dayMs);
}

function addDays(date: Date, days: number): Date {
  const utcDate: Date = toUtcDateOnly(date);
  utcDate.setUTCDate(utcDate.getUTCDate() + days);
  return utcDate;
}

function addYears(date: Date, years: number): Date {
  const utcDate: Date = toUtcDateOnly(date);
  utcDate.setUTCFullYear(utcDate.getUTCFullYear() + years);
  return utcDate;
}

export function calculateDenialRate(claims: Claim[]): number {
  if (claims.length === 0) {
    throw new Error("Claims array cannot be empty.");
  }

  const deniedCount: number = claims.filter((claim: Claim) => claim.status === "denied").length;
  return percentage(deniedCount, claims.length, 2);
}

export function denialRateByPayer(claims: Claim[]): Record<string, number> {
  const groupedByPayer: Record<string, Claim[]> = groupClaimsBy(claims, "payerName");

  return Object.entries(groupedByPayer).reduce<Record<string, number>>(
    (rates: Record<string, number>, [payerName, payerClaims]: [string, Claim[]]) => {
      const deniedCount: number = payerClaims.filter((claim: Claim) => claim.status === "denied").length;
      rates[payerName] = percentage(deniedCount, payerClaims.length, 2);
      return rates;
    },
    {}
  );
}

export function denialRateByLocation(claims: Claim[]): Record<string, number> {
  const groupedByLocation: Record<string, Claim[]> = groupClaimsBy(claims, "locationId");

  return Object.entries(groupedByLocation).reduce<Record<string, number>>(
    (rates: Record<string, number>, [locationId, locationClaims]: [string, Claim[]]) => {
      const deniedCount: number = locationClaims.filter((claim: Claim) => claim.status === "denied").length;
      rates[locationId] = percentage(deniedCount, locationClaims.length, 2);
      return rates;
    },
    {}
  );
}

export function flagHighDenialPayers(claims: Claim[], threshold: number = 8): string[] {
  const rates: Record<string, number> = denialRateByPayer(claims);

  return Object.entries(rates)
    .filter(([, rate]: [string, number]) => rate > threshold)
    .map(([payerName]: [string, number]) => payerName);
}

export function calculateNoShowCost(
  appointments: Appointment[],
  location: Location,
  weekEndingDate: string
): number {
  const weekEnd: Date | null = parseDate(weekEndingDate);
  if (!weekEnd) {
    return 0;
  }

  const weekStart: Date = addDays(weekEnd, -6);

  const totalLostRevenue: number = appointments.reduce((sum: number, appointment: Appointment) => {
    if (appointment.locationId !== location.locationId || appointment.status !== "no_show") {
      return sum;
    }

    const scheduledDate: Date | null = parseDate(appointment.scheduledDate);
    if (!scheduledDate) {
      return sum;
    }

    const inRange: boolean = scheduledDate >= weekStart && scheduledDate <= weekEnd;
    if (!inRange) {
      return sum;
    }

    const feeByServiceType: Record<ServiceType, number> = location.averageConsultationFee;
    const fee: number = feeByServiceType[appointment.serviceType] ?? 0;
    return sum + (Number.isFinite(fee) ? fee : 0);
  }, 0);

  return roundTo(totalLostRevenue, 2);
}

export function noShowRateByLocation(appointments: Appointment[]): Record<string, number> {
  const groupedByLocation: Record<string, Appointment[]> = appointments.reduce<Record<string, Appointment[]>>(
    (groups: Record<string, Appointment[]>, appointment: Appointment) => {
      if (!groups[appointment.locationId]) {
        groups[appointment.locationId] = [];
      }

      groups[appointment.locationId].push(appointment);
      return groups;
    },
    {}
  );

  return Object.entries(groupedByLocation).reduce<Record<string, number>>(
    (rates: Record<string, number>, [locationId, locationAppointments]: [string, Appointment[]]) => {
      const noShowCount: number = locationAppointments.filter(
        (appointment: Appointment) => appointment.status === "no_show"
      ).length;

      rates[locationId] = percentage(noShowCount, locationAppointments.length, 2);
      return rates;
    },
    {}
  );
}

export function flagHighNoShowLocations(
  appointments: Appointment[],
  threshold: number = 20
): string[] {
  const rates: Record<string, number> = noShowRateByLocation(appointments);

  return Object.entries(rates)
    .filter(([, rate]: [string, number]) => rate > threshold)
    .map(([locationId]: [string, number]) => locationId);
}

function calculatePercentComplete(hoursLogged: number, hoursRequired: number): number {
  if (hoursRequired <= 0) {
    return 100;
  }

  return roundTo((hoursLogged / hoursRequired) * 100, 1);
}

function resolveComplianceStatus(
  hoursLogged: number,
  hoursRequired: number,
  cycleStartDate: Date | null,
  asOfDate: Date,
  percentComplete: number
): { status: CMEStatus; daysRemainingInCycle: number } {
  if (!cycleStartDate) {
    const fallbackStatus: CMEStatus = hoursLogged >= hoursRequired ? "complete" : "at_risk";
    return { status: fallbackStatus, daysRemainingInCycle: 0 };
  }

  const cycleEndDate: Date = addDays(addYears(cycleStartDate, 1), -1);
  const daysRemainingInCycle: number = diffCalendarDays(asOfDate, cycleEndDate);

  if (hoursLogged >= hoursRequired) {
    return { status: "complete", daysRemainingInCycle };
  }

  if (daysRemainingInCycle < 0) {
    return { status: "overdue", daysRemainingInCycle };
  }

  const totalCycleDays: number = Math.max(1, diffCalendarDays(cycleStartDate, cycleEndDate) + 1);
  const elapsedDaysRaw: number = diffCalendarDays(cycleStartDate, asOfDate) + 1;
  const elapsedDays: number = Math.min(Math.max(elapsedDaysRaw, 0), totalCycleDays);
  const elapsedSharePercent: number = (elapsedDays / totalCycleDays) * 100;

  if (elapsedSharePercent - percentComplete > 15) {
    return { status: "at_risk", daysRemainingInCycle };
  }

  return { status: "on_track", daysRemainingInCycle };
}

export function generateCMEReport(clinicians: Clinician[], asOfDate: string): CMEReport[] {
  const asOf: Date | null = parseDate(asOfDate);
  if (!asOf) {
    return [];
  }

  return clinicians.map((clinician: Clinician) => {
    const hoursRemaining: number = Math.max(0, clinician.cmeHoursRequired - clinician.cmeHoursLogged);
    const percentComplete: number = calculatePercentComplete(clinician.cmeHoursLogged, clinician.cmeHoursRequired);

    const cycleStartDate: Date | null = parseDate(clinician.cmeYearStartDate);
    const compliance: { status: CMEStatus; daysRemainingInCycle: number } = resolveComplianceStatus(
      clinician.cmeHoursLogged,
      clinician.cmeHoursRequired,
      cycleStartDate,
      asOf,
      percentComplete
    );

    const licenceExpiry: Date | null = parseDate(clinician.licenceExpiryDate);
    const licenceDaysRemaining: number = licenceExpiry ? diffCalendarDays(asOf, licenceExpiry) : 0;

    return {
      clinicianId: clinician.clinicianId,
      fullName: `${clinician.firstName} ${clinician.lastName}`,
      role: clinician.role,
      locationId: clinician.locationId,
      hoursRequired: clinician.cmeHoursRequired,
      hoursLogged: clinician.cmeHoursLogged,
      hoursRemaining,
      percentComplete,
      daysRemainingInCycle: compliance.daysRemainingInCycle,
      complianceStatus: compliance.status,
      licenceExpiryDate: clinician.licenceExpiryDate,
      licenceDaysRemaining,
    };
  });
}

export function getCliniciansAtRisk(clinicians: Clinician[], asOfDate: string): Clinician[] {
  const report: CMEReport[] = generateCMEReport(clinicians, asOfDate);
  const atRiskIds: Set<string> = new Set(
    report
      .filter((entry: CMEReport) => entry.complianceStatus === "at_risk" || entry.complianceStatus === "overdue")
      .map((entry: CMEReport) => entry.clinicianId)
  );

  return clinicians.filter((clinician: Clinician) => atRiskIds.has(clinician.clinicianId));
}

export function getCliniciansWithExpiringLicences(
  clinicians: Clinician[],
  asOfDate: string,
  daysThreshold: number
): Clinician[] {
  const asOf: Date | null = parseDate(asOfDate);
  if (!asOf) {
    return [];
  }

  return clinicians.filter((clinician: Clinician) => {
    const licenceDate: Date | null = parseDate(clinician.licenceExpiryDate);
    if (!licenceDate) {
      return false;
    }

    const daysUntilExpiry: number = diffCalendarDays(asOf, licenceDate);
    return daysUntilExpiry >= 0 && daysUntilExpiry <= daysThreshold;
  });
}
