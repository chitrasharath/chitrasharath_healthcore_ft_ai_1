import {
  Appointment,
  Claim,
  Clinician,
  Location,
  ServiceType,
} from "../types/models.js";
import {
  filterAppointmentsByStatus,
  filterClaims,
  groupClaimsBy,
  sortAppointmentsByDate,
  sortClaimsById,
} from "../utils/collections.js";
import {
  binarySearchClaimById,
  findClaimById,
  findClinicianById,
} from "../utils/search.js";
import {
  calculateDenialRate,
  calculateNoShowCost,
  denialRateByLocation,
  denialRateByPayer,
  flagHighDenialPayers,
  flagHighNoShowLocations,
  generateCMEReport,
  getCliniciansAtRisk,
  getCliniciansWithExpiringLicences,
  noShowRateByLocation,
} from "../utils/transformations.js";
import {
  isDenialRateAboveThreshold,
  isNoShowRateAboveThreshold,
  validateClaim,
  validateClinician,
} from "../utils/validations.js";

function fail(message: string): never {
  throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, label: string): void {
  if (actual !== expected) {
    fail(`${label} | expected: ${String(expected)} | actual: ${String(actual)}`);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown, label: string): void {
  const actualSerialized: string = JSON.stringify(actual);
  const expectedSerialized: string = JSON.stringify(expected);

  if (actualSerialized !== expectedSerialized) {
    fail(`${label} | expected: ${expectedSerialized} | actual: ${actualSerialized}`);
  }
}

function assertOk(condition: boolean, label: string): void {
  if (!condition) {
    fail(`${label} | condition was false`);
  }
}

function assertThrows(fn: () => unknown, label: string): void {
  try {
    fn();
    fail(`${label} | expected function to throw`);
  } catch {
    return;
  }
}

const locations: Location[] = [
  {
    locationId: "us-tx-001",
    name: "HealthCore Austin Central",
    city: "Austin",
    stateOrCountry: "TX",
    country: "US",
    phone: "(512) 340-8800",
    averageConsultationFee: {
      primary_care: 180,
      chronic_disease: 220,
      preventive: 150,
      specialist: 320,
      womens_health: 240,
      paediatric: 175,
      mental_health: 200,
    },
  },
  {
    locationId: "us-fl-001",
    name: "HealthCore Miami",
    city: "Miami",
    stateOrCountry: "FL",
    country: "US",
    phone: "(305) 510-7700",
    averageConsultationFee: {
      primary_care: 195,
      chronic_disease: 235,
      preventive: 160,
      specialist: 340,
      womens_health: 255,
      paediatric: 185,
      mental_health: 215,
    },
  },
  {
    locationId: "us-ga-001",
    name: "HealthCore Atlanta",
    city: "Atlanta",
    stateOrCountry: "GA",
    country: "US",
    phone: "(404) 330-9900",
    averageConsultationFee: {
      primary_care: 170,
      chronic_disease: 210,
      preventive: 145,
      specialist: 310,
      womens_health: 230,
      paediatric: 165,
      mental_health: 190,
    },
  },
];

const claims: Claim[] = [
  {
    claimId: "CLM-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-10",
    claimAmount: 180,
    status: "approved",
    resubmitted: false,
  },
  {
    claimId: "CLM-000002",
    patientId: "HC-B7K442",
    locationId: "us-fl-001",
    serviceType: "specialist",
    payerName: "Aetna",
    payerId: "AET002",
    submissionDate: "2025-03-11",
    claimAmount: 340,
    status: "denied",
    denialReason: "missing_authorisation",
    resubmitted: false,
  },
  {
    claimId: "CLM-000003",
    patientId: "HC-C2M881",
    locationId: "us-ga-001",
    serviceType: "chronic_disease",
    payerName: "Medicare",
    payerId: "MED003",
    submissionDate: "2025-03-12",
    claimAmount: 210,
    status: "approved",
    resubmitted: false,
  },
  {
    claimId: "CLM-000004",
    patientId: "HC-D9P553",
    locationId: "us-tx-001",
    serviceType: "preventive",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-13",
    claimAmount: 150,
    status: "denied",
    denialReason: "coding_error",
    resubmitted: true,
  },
  {
    claimId: "CLM-000005",
    patientId: "HC-E4Q117",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    payerName: "Cigna",
    payerId: "CIG004",
    submissionDate: "2025-03-14",
    claimAmount: 215,
    status: "pending",
    resubmitted: false,
  },
];

const appointments: Appointment[] = [
  {
    appointmentId: "APT-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    scheduledDate: "2025-03-10",
    scheduledTime: "09:00",
    status: "completed",
    confirmedAt: "2025-03-09T14:00:00Z",
  },
  {
    appointmentId: "APT-000002",
    patientId: "HC-F6R228",
    locationId: "us-fl-001",
    serviceType: "specialist",
    scheduledDate: "2025-03-11",
    scheduledTime: "11:30",
    status: "no_show",
    noShowReason: "Patient did not call to cancel",
  },
  {
    appointmentId: "APT-000003",
    patientId: "HC-G1S774",
    locationId: "us-tx-001",
    serviceType: "chronic_disease",
    scheduledDate: "2025-03-12",
    scheduledTime: "14:00",
    status: "no_show",
    noShowReason: "Unreachable before appointment",
  },
  {
    appointmentId: "APT-000004",
    patientId: "HC-H8T390",
    locationId: "us-ga-001",
    serviceType: "preventive",
    scheduledDate: "2025-03-13",
    scheduledTime: "10:00",
    status: "completed",
    confirmedAt: "2025-03-12T09:30:00Z",
  },
  {
    appointmentId: "APT-000005",
    patientId: "HC-I5U661",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    scheduledDate: "2025-03-14",
    scheduledTime: "16:00",
    status: "no_show",
    noShowReason: "Transportation issue reported",
  },
];

const clinicians: Clinician[] = [
  {
    clinicianId: "CLN-000001",
    firstName: "Marcus",
    lastName: "Reid",
    role: "physician",
    locationId: "us-tx-001",
    licenceState: "TX",
    licenceExpiryDate: "2026-06-30",
    cmeHoursRequired: 40,
    cmeHoursLogged: 28,
    cmeYearStartDate: "2025-01-01",
  },
  {
    clinicianId: "CLN-000002",
    firstName: "Sandra",
    lastName: "Flores",
    role: "nurse_practitioner",
    locationId: "us-fl-001",
    licenceState: "FL",
    licenceExpiryDate: "2025-05-15",
    cmeHoursRequired: 30,
    cmeHoursLogged: 6,
    cmeYearStartDate: "2025-01-01",
  },
  {
    clinicianId: "CLN-000003",
    firstName: "David",
    lastName: "Okafor",
    role: "physician",
    locationId: "us-ga-001",
    licenceState: "GA",
    licenceExpiryDate: "2027-01-01",
    cmeHoursRequired: 40,
    cmeHoursLogged: 40,
    cmeYearStartDate: "2025-01-01",
  },
];

function assertCollections(): void {
  assertEqual(filterClaims(claims, { locationId: "us-tx-001" }).length, 2, "filterClaims by location");
  assertEqual(filterAppointmentsByStatus(appointments, ["no_show"]).length, 3, "filterAppointmentsByStatus no_show");
  assertEqual(filterAppointmentsByStatus(appointments, []).length, 0, "filterAppointmentsByStatus empty statuses");

  const sortedClaimIds: string[] = sortClaimsById(claims, "asc").map((item: Claim) => item.claimId);
  assertDeepEqual(
    sortedClaimIds,
    ["CLM-000001", "CLM-000002", "CLM-000003", "CLM-000004", "CLM-000005"],
    "sortClaimsById asc"
  );

  const sortedAppointmentIds: string[] = sortAppointmentsByDate(appointments, "desc").map(
    (item: Appointment) => item.appointmentId
  );
  assertDeepEqual(
    sortedAppointmentIds,
    ["APT-000005", "APT-000004", "APT-000003", "APT-000002", "APT-000001"],
    "sortAppointmentsByDate desc"
  );

  const groupedByPayer: Record<string, Claim[]> = groupClaimsBy(claims, "payerName");
  assertEqual(groupedByPayer.BlueCross.length, 2, "groupClaimsBy BlueCross length");
  assertEqual(groupedByPayer.Aetna.length, 1, "groupClaimsBy Aetna length");
}

function assertSearch(): void {
  assertEqual(findClaimById(claims, "CLM-000003")?.patientId, "HC-C2M881", "findClaimById existing");
  assertEqual(findClaimById(claims, "CLM-999999"), null, "findClaimById missing");

  assertEqual(findClinicianById(clinicians, "CLN-000002")?.firstName, "Sandra", "findClinicianById existing");
  assertEqual(findClinicianById(clinicians, "CLN-999999"), null, "findClinicianById missing");

  const sortedClaims: Claim[] = sortClaimsById(claims, "asc");
  assertEqual(binarySearchClaimById(sortedClaims, "CLM-000004"), 3, "binarySearchClaimById existing");
  assertEqual(binarySearchClaimById(sortedClaims, "CLM-999999"), -1, "binarySearchClaimById missing");
}

function assertTransformations(): void {
  assertEqual(calculateDenialRate(claims), 40, "calculateDenialRate");
  assertThrows((): number => calculateDenialRate([]), "calculateDenialRate throws on empty array");

  const payerRates: Record<string, number> = denialRateByPayer(claims);
  assertEqual(payerRates.BlueCross, 50, "denialRateByPayer BlueCross");
  assertEqual(payerRates.Aetna, 100, "denialRateByPayer Aetna");

  const locationRates: Record<string, number> = denialRateByLocation(claims);
  assertEqual(locationRates["us-tx-001"], 50, "denialRateByLocation us-tx-001");
  assertEqual(locationRates["us-ga-001"], 0, "denialRateByLocation us-ga-001");

  const highDenialPayers: string[] = flagHighDenialPayers(claims);
  assertDeepEqual(highDenialPayers, ["BlueCross", "Aetna"], "flagHighDenialPayers");

  assertEqual(calculateNoShowCost(appointments, locations[1], "2025-03-14"), 555, "calculateNoShowCost in range");
  assertEqual(calculateNoShowCost(appointments, locations[1], "not-a-date"), 0, "calculateNoShowCost invalid date");

  const noShowRates: Record<string, number> = noShowRateByLocation(appointments);
  assertEqual(noShowRates["us-fl-001"], 100, "noShowRateByLocation us-fl-001");
  assertEqual(noShowRates["us-ga-001"], 0, "noShowRateByLocation us-ga-001");

  assertDeepEqual(flagHighNoShowLocations(appointments), ["us-tx-001", "us-fl-001"], "flagHighNoShowLocations");

  const cmeReport = generateCMEReport(clinicians, "2025-04-15");
  assertEqual(cmeReport.length, 3, "generateCMEReport count");
  assertEqual(cmeReport[2].complianceStatus, "complete", "generateCMEReport complete clinician");
  assertEqual(generateCMEReport(clinicians, "invalid-date").length, 0, "generateCMEReport invalid date");

  assertEqual(getCliniciansAtRisk(clinicians, "2025-04-15").length, 0, "getCliniciansAtRisk");
  assertEqual(
    getCliniciansWithExpiringLicences(clinicians, "2025-04-15", 90).length,
    1,
    "getCliniciansWithExpiringLicences 90 days"
  );
  assertEqual(
    getCliniciansWithExpiringLicences(clinicians, "invalid-date", 90).length,
    0,
    "getCliniciansWithExpiringLicences invalid date"
  );
}

function assertValidations(): void {
  const knownLocationIds: string[] = locations.map((location: Location) => location.locationId);

  assertDeepEqual(validateClaim(claims[0], knownLocationIds), { valid: true, errors: [] }, "validateClaim valid");

  const invalidClaim: Claim = {
    ...claims[0],
    claimAmount: -10,
    submissionDate: "3025-01-01",
    locationId: "unknown",
    status: "denied",
    denialReason: undefined,
    patientId: "BAD-123",
  };

  const invalidClaimResult = validateClaim(invalidClaim, knownLocationIds);
  assertEqual(invalidClaimResult.valid, false, "validateClaim invalid flag");
  assertEqual(invalidClaimResult.errors.length, 5, "validateClaim invalid errors length");

  assertDeepEqual(validateClinician(clinicians[0]), { valid: true, errors: [] }, "validateClinician valid");

  const invalidClinician: Clinician = {
    ...clinicians[1],
    cmeHoursRequired: -1,
    cmeHoursLogged: -2,
    licenceExpiryDate: "2020-01-01",
  };

  const invalidClinicianResult = validateClinician(invalidClinician);
  assertEqual(invalidClinicianResult.valid, false, "validateClinician invalid flag");
  assertEqual(invalidClinicianResult.errors.length, 3, "validateClinician invalid errors length");

  assertEqual(isDenialRateAboveThreshold(12), true, "isDenialRateAboveThreshold above");
  assertEqual(isDenialRateAboveThreshold(8), false, "isDenialRateAboveThreshold boundary");
  assertEqual(isNoShowRateAboveThreshold(21), true, "isNoShowRateAboveThreshold above");
  assertEqual(isNoShowRateAboveThreshold(20), false, "isNoShowRateAboveThreshold boundary");
}

function assertEdgeCases(): void {
  const locationWithNoFees: Location = {
    locationId: "us-test-001",
    name: "Test",
    city: "Test",
    stateOrCountry: "TX",
    country: "US",
    phone: "(000) 000-0000",
    averageConsultationFee: {
      primary_care: 0,
      chronic_disease: 0,
      preventive: 0,
      specialist: 0,
      womens_health: 0,
      paediatric: 0,
      mental_health: 0,
    },
  };

  const noFeeAppointments: Appointment[] = [
    {
      appointmentId: "APT-TEST-001",
      patientId: "HC-ZZZ999",
      locationId: "us-test-001",
      serviceType: "mental_health" as ServiceType,
      scheduledDate: "2025-03-14",
      scheduledTime: "10:00",
      status: "no_show",
      noShowReason: "Test",
    },
  ];

  assertEqual(calculateNoShowCost(noFeeAppointments, locationWithNoFees, "2025-03-14"), 0, "calculateNoShowCost zero fees");
}

function runTests(): void {
  assertCollections();
  assertSearch();
  assertTransformations();
  assertValidations();
  assertEdgeCases();

  console.log("All lightweight tests passed.");
}

runTests();
