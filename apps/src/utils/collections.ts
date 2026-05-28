import { Appointment, AppointmentStatus, Claim } from "../types/models.js";

export function filterClaims(
  claims: Claim[],
  filters: Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>
): Claim[] {
  return claims.filter((claim: Claim) => {
    const matchesLocation: boolean = filters.locationId === undefined || claim.locationId === filters.locationId;
    const matchesStatus: boolean = filters.status === undefined || claim.status === filters.status;
    const matchesPayer: boolean = filters.payerName === undefined || claim.payerName === filters.payerName;
    const matchesServiceType: boolean = filters.serviceType === undefined || claim.serviceType === filters.serviceType;

    return matchesLocation && matchesStatus && matchesPayer && matchesServiceType;
  });
}

export function filterAppointmentsByStatus(
  appointments: Appointment[],
  status: AppointmentStatus[]
): Appointment[] {
  if (status.length === 0) {
    return [];
  }

  const statusSet: Set<AppointmentStatus> = new Set(status);
  return appointments.filter((appointment: Appointment) => statusSet.has(appointment.status));
}

export function sortClaimsById(claims: Claim[], direction: "asc" | "desc"): Claim[] {
  const sortedClaims: Claim[] = [...claims].sort((a: Claim, b: Claim) => a.claimId.localeCompare(b.claimId));
  return direction === "asc" ? sortedClaims : sortedClaims.reverse();
}

function dateToTimestamp(dateInput: string): number {
  const timestamp: number = Date.parse(dateInput);
  return Number.isNaN(timestamp) ? Number.POSITIVE_INFINITY : timestamp;
}

export function sortAppointmentsByDate(
  appointments: Appointment[],
  direction: "asc" | "desc"
): Appointment[] {
  const sortedAppointments: Appointment[] = [...appointments].sort(
    (a: Appointment, b: Appointment) => dateToTimestamp(a.scheduledDate) - dateToTimestamp(b.scheduledDate)
  );

  return direction === "asc" ? sortedAppointments : sortedAppointments.reverse();
}

export function groupClaimsBy(
  claims: Claim[],
  key: "locationId" | "payerName" | "status" | "serviceType"
): Record<string, Claim[]> {
  return claims.reduce<Record<string, Claim[]>>((grouped: Record<string, Claim[]>, claim: Claim) => {
    const groupKey: string = claim[key];

    if (!grouped[groupKey]) {
      grouped[groupKey] = [];
    }

    grouped[groupKey].push(claim);
    return grouped;
  }, {});
}
