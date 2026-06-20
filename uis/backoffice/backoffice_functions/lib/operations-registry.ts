// Copied from apps/src/main.ts — keep in sync with buildOperations() there.
import type { Appointment, Claim, Clinician, Location } from "@healthcore/src/types/models";
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
} from "@healthcore/src/utils/transformations";
import {
  filterAppointmentsByStatus,
  filterClaims,
  groupClaimsBy,
  sortAppointmentsByDate,
  sortClaimsById,
} from "@healthcore/src/utils/collections";
import { binarySearchClaimById, findClaimById, findClinicianById } from "@healthcore/src/utils/search";
import {
  isDenialRateAboveThreshold,
  isNoShowRateAboveThreshold,
  validateClaim,
  validateClinician,
} from "@healthcore/src/utils/validations";
import {
  sampleAppointments,
  sampleClaims,
  sampleClinicians,
  sampleLocations,
} from "@backoffice/backoffice-functions/lib/sample-data";
import type {
  OperationDefinition,
  ParamOption,
  RawParamValue,
} from "@backoffice/backoffice-functions/lib/operation-types";

const claimStatusOptions: ParamOption[] = [
  { label: "submitted", value: "submitted" },
  { label: "approved", value: "approved" },
  { label: "denied", value: "denied" },
  { label: "pending", value: "pending" },
  { label: "appealed", value: "appealed" },
];

const appointmentStatusOptions: ParamOption[] = [
  { label: "scheduled", value: "scheduled" },
  { label: "confirmed", value: "confirmed" },
  { label: "completed", value: "completed" },
  { label: "no_show", value: "no_show" },
  { label: "cancelled", value: "cancelled" },
];

const serviceTypeOptions: ParamOption[] = [
  { label: "primary_care", value: "primary_care" },
  { label: "chronic_disease", value: "chronic_disease" },
  { label: "preventive", value: "preventive" },
  { label: "specialist", value: "specialist" },
  { label: "womens_health", value: "womens_health" },
  { label: "paediatric", value: "paediatric" },
  { label: "mental_health", value: "mental_health" },
];

function locationOptions(): ParamOption[] {
  return sampleLocations.map((location: Location) => ({ label: location.locationId, value: location.locationId }));
}

function claimOptions(): ParamOption[] {
  return sampleClaims.map((claim: Claim) => ({ label: claim.claimId, value: claim.claimId }));
}

function clinicianOptions(): ParamOption[] {
  return sampleClinicians.map((clinician: Clinician) => ({ label: clinician.clinicianId, value: clinician.clinicianId }));
}

function payerOptions(): ParamOption[] {
  const uniquePayers: string[] = Array.from(new Set(sampleClaims.map((claim: Claim) => claim.payerName)));
  return uniquePayers.map((payerName: string) => ({ label: payerName, value: payerName }));
}

function getStringParam(params: Record<string, RawParamValue>, key: string, fallback: string = ""): string {
  const value: RawParamValue | undefined = params[key];
  if (Array.isArray(value)) {
    return value[0] ?? fallback;
  }

  return value ?? fallback;
}

function getNumberParam(params: Record<string, RawParamValue>, key: string, fallback: number): number {
  const raw: string = getStringParam(params, key, String(fallback));
  const parsed: number = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getArrayParam(params: Record<string, RawParamValue>, key: string): string[] {
  const value: RawParamValue | undefined = params[key];
  if (Array.isArray(value)) {
    return value;
  }

  return value ? [value] : [];
}

function findLocationById(locationId: string): Location {
  const location: Location | undefined = sampleLocations.find((item: Location) => item.locationId === locationId);
  return location ?? sampleLocations[0];
}

function findClaimSampleById(claimId: string): Claim {
  const claim: Claim | undefined = sampleClaims.find((item: Claim) => item.claimId === claimId);
  return claim ?? sampleClaims[0];
}

function findClinicianSampleById(clinicianId: string): Clinician {
  const clinician: Clinician | undefined = sampleClinicians.find((item: Clinician) => item.clinicianId === clinicianId);
  return clinician ?? sampleClinicians[0];
}

function buildOperationsBody(): OperationDefinition[] {
  return [
    {
      id: "filterClaims",
      label: "filterClaims",
      description: "Filter claims by optional location, status, payer, and service type.",
      params: [
        { key: "locationId", label: "locationId", type: "select", options: [{ label: "Any", value: "" }, ...locationOptions()] },
        { key: "status", label: "status", type: "select", options: [{ label: "Any", value: "" }, ...claimStatusOptions] },
        { key: "payerName", label: "payerName", type: "select", options: [{ label: "Any", value: "" }, ...payerOptions()] },
        { key: "serviceType", label: "serviceType", type: "select", options: [{ label: "Any", value: "" }, ...serviceTypeOptions] },
      ],
      run: (params: Record<string, RawParamValue>): Claim[] => {
        const locationId: string = getStringParam(params, "locationId");
        const status: string = getStringParam(params, "status");
        const payerName: string = getStringParam(params, "payerName");
        const serviceType: string = getStringParam(params, "serviceType");

        const filters: Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">> = {};
        if (locationId) {
          filters.locationId = locationId;
        }
        if (status) {
          filters.status = status as Claim["status"];
        }
        if (payerName) {
          filters.payerName = payerName;
        }
        if (serviceType) {
          filters.serviceType = serviceType as Claim["serviceType"];
        }

        return filterClaims(sampleClaims, filters);
      },
    },
    {
      id: "filterAppointmentsByStatus",
      label: "filterAppointmentsByStatus",
      description: "Filter appointments by one or more statuses.",
      params: [
        {
          key: "statuses",
          label: "statuses",
          type: "multiselect",
          options: appointmentStatusOptions,
          defaultValue: ["no_show"],
        },
      ],
      run: (params: Record<string, RawParamValue>): Appointment[] => {
        const selectedStatuses: string[] = getArrayParam(params, "statuses");
        return filterAppointmentsByStatus(sampleAppointments, selectedStatuses as Appointment["status"][]);
      },
    },
    {
      id: "sortClaimsById",
      label: "sortClaimsById",
      description: "Sort claims by claimId in ascending or descending order.",
      params: [{ key: "direction", label: "direction", type: "select", options: [{ label: "asc", value: "asc" }, { label: "desc", value: "desc" }], defaultValue: "asc" }],
      run: (params: Record<string, RawParamValue>): Claim[] => sortClaimsById(sampleClaims, getStringParam(params, "direction", "asc") as "asc" | "desc"),
    },
    {
      id: "sortAppointmentsByDate",
      label: "sortAppointmentsByDate",
      description: "Sort appointments by scheduledDate.",
      params: [{ key: "direction", label: "direction", type: "select", options: [{ label: "asc", value: "asc" }, { label: "desc", value: "desc" }], defaultValue: "asc" }],
      run: (params: Record<string, RawParamValue>): Appointment[] =>
        sortAppointmentsByDate(sampleAppointments, getStringParam(params, "direction", "asc") as "asc" | "desc"),
    },
    {
      id: "groupClaimsBy",
      label: "groupClaimsBy",
      description: "Group claims by locationId, payerName, status, or serviceType.",
      params: [{ key: "key", label: "key", type: "select", options: [{ label: "locationId", value: "locationId" }, { label: "payerName", value: "payerName" }, { label: "status", value: "status" }, { label: "serviceType", value: "serviceType" }], defaultValue: "payerName" }],
      run: (params: Record<string, RawParamValue>): Record<string, Claim[]> =>
        groupClaimsBy(sampleClaims, getStringParam(params, "key", "payerName") as "locationId" | "payerName" | "status" | "serviceType"),
    },
    {
      id: "findClaimById",
      label: "findClaimById",
      description: "Find one claim by claimId.",
      params: [{ key: "claimId", label: "claimId", type: "select", options: claimOptions(), defaultValue: "CLM-000003" }],
      run: (params: Record<string, RawParamValue>): Claim | null => findClaimById(sampleClaims, getStringParam(params, "claimId", "CLM-000003")),
    },
    {
      id: "findClinicianById",
      label: "findClinicianById",
      description: "Find one clinician by clinicianId.",
      params: [{ key: "clinicianId", label: "clinicianId", type: "select", options: clinicianOptions(), defaultValue: "CLN-000002" }],
      run: (params: Record<string, RawParamValue>): Clinician | null =>
        findClinicianById(sampleClinicians, getStringParam(params, "clinicianId", "CLN-000002")),
    },
    {
      id: "binarySearchClaimById",
      label: "binarySearchClaimById",
      description: "Binary search on claims sorted ascending by claimId.",
      params: [{ key: "targetId", label: "targetId", type: "select", options: claimOptions(), defaultValue: "CLM-000004" }],
      run: (params: Record<string, RawParamValue>): number => {
        const sortedClaims: Claim[] = sortClaimsById(sampleClaims, "asc");
        return binarySearchClaimById(sortedClaims, getStringParam(params, "targetId", "CLM-000004"));
      },
    },
    {
      id: "calculateDenialRate",
      label: "calculateDenialRate",
      description: "Calculate overall denial rate for sample claims.",
      params: [],
      run: (): number => calculateDenialRate(sampleClaims),
    },
    {
      id: "denialRateByPayer",
      label: "denialRateByPayer",
      description: "Calculate denial rate grouped by payer.",
      params: [],
      run: (): Record<string, number> => denialRateByPayer(sampleClaims),
    },
    {
      id: "denialRateByLocation",
      label: "denialRateByLocation",
      description: "Calculate denial rate grouped by location.",
      params: [],
      run: (): Record<string, number> => denialRateByLocation(sampleClaims),
    },
    {
      id: "flagHighDenialPayers",
      label: "flagHighDenialPayers",
      description: "Return payers whose denial rate exceeds threshold.",
      params: [{ key: "threshold", label: "threshold", type: "number", defaultValue: "8" }],
      run: (params: Record<string, RawParamValue>): string[] =>
        flagHighDenialPayers(sampleClaims, getNumberParam(params, "threshold", 8)),
    },
    {
      id: "calculateNoShowCost",
      label: "calculateNoShowCost",
      description: "Calculate no-show revenue loss for location and week ending date.",
      params: [
        { key: "locationId", label: "locationId", type: "select", options: locationOptions(), defaultValue: "us-fl-001" },
        { key: "weekEndingDate", label: "weekEndingDate", type: "date", defaultValue: "2025-03-14" },
      ],
      run: (params: Record<string, RawParamValue>): number => {
        const locationId: string = getStringParam(params, "locationId", "us-fl-001");
        const weekEndingDate: string = getStringParam(params, "weekEndingDate", "2025-03-14");
        return calculateNoShowCost(sampleAppointments, findLocationById(locationId), weekEndingDate);
      },
    },
    {
      id: "noShowRateByLocation",
      label: "noShowRateByLocation",
      description: "Calculate no-show rates grouped by location.",
      params: [],
      run: (): Record<string, number> => noShowRateByLocation(sampleAppointments),
    },
    {
      id: "flagHighNoShowLocations",
      label: "flagHighNoShowLocations",
      description: "Return locations where no-show rate exceeds threshold.",
      params: [{ key: "threshold", label: "threshold", type: "number", defaultValue: "20" }],
      run: (params: Record<string, RawParamValue>): string[] =>
        flagHighNoShowLocations(sampleAppointments, getNumberParam(params, "threshold", 20)),
    },
    {
      id: "generateCMEReport",
      label: "generateCMEReport",
      description: "Generate CME report entries for all sample clinicians.",
      params: [{ key: "asOfDate", label: "asOfDate", type: "date", defaultValue: "2025-04-15" }],
      run: (params: Record<string, RawParamValue>) => generateCMEReport(sampleClinicians, getStringParam(params, "asOfDate", "2025-04-15")),
    },
    {
      id: "getCliniciansAtRisk",
      label: "getCliniciansAtRisk",
      description: "Find clinicians with at_risk or overdue CME status.",
      params: [{ key: "asOfDate", label: "asOfDate", type: "date", defaultValue: "2025-04-15" }],
      run: (params: Record<string, RawParamValue>): Clinician[] =>
        getCliniciansAtRisk(sampleClinicians, getStringParam(params, "asOfDate", "2025-04-15")),
    },
    {
      id: "getCliniciansWithExpiringLicences",
      label: "getCliniciansWithExpiringLicences",
      description: "Find clinicians with licences expiring within daysThreshold.",
      params: [
        { key: "asOfDate", label: "asOfDate", type: "date", defaultValue: "2025-04-15" },
        { key: "daysThreshold", label: "daysThreshold", type: "number", defaultValue: "90" },
      ],
      run: (params: Record<string, RawParamValue>): Clinician[] =>
        getCliniciansWithExpiringLicences(
          sampleClinicians,
          getStringParam(params, "asOfDate", "2025-04-15"),
          getNumberParam(params, "daysThreshold", 90)
        ),
    },
    {
      id: "validateClaim",
      label: "validateClaim",
      description: "Validate a selected claim with chosen known location list scope.",
      params: [
        { key: "claimId", label: "claimId", type: "select", options: claimOptions(), defaultValue: "CLM-000001" },
        {
          key: "knownLocationScope",
          label: "knownLocationScope",
          type: "select",
          options: [
            { label: "all_sample_locations", value: "all" },
            { label: "exclude_selected_claim_location", value: "exclude_claim" },
          ],
          defaultValue: "all",
        },
      ],
      run: (params: Record<string, RawParamValue>): ReturnType<typeof validateClaim> => {
        const claimId: string = getStringParam(params, "claimId", "CLM-000001");
        const selectedClaim: Claim = findClaimSampleById(claimId);
        const scope: string = getStringParam(params, "knownLocationScope", "all");
        const knownLocationIds: string[] = sampleLocations
          .map((location: Location) => location.locationId)
          .filter((locationId: string) => scope !== "exclude_claim" || locationId !== selectedClaim.locationId);

        return validateClaim(selectedClaim, knownLocationIds);
      },
    },
    {
      id: "validateClinician",
      label: "validateClinician",
      description: "Validate a selected clinician record.",
      params: [{ key: "clinicianId", label: "clinicianId", type: "select", options: clinicianOptions(), defaultValue: "CLN-000001" }],
      run: (params: Record<string, RawParamValue>): ReturnType<typeof validateClinician> =>
        validateClinician(findClinicianSampleById(getStringParam(params, "clinicianId", "CLN-000001"))),
    },
    {
      id: "isDenialRateAboveThreshold",
      label: "isDenialRateAboveThreshold",
      description: "Check if a denial rate exceeds threshold.",
      params: [
        { key: "rate", label: "rate", type: "number", defaultValue: "12" },
        { key: "threshold", label: "threshold", type: "number", defaultValue: "8" },
      ],
      run: (params: Record<string, RawParamValue>): boolean =>
        isDenialRateAboveThreshold(getNumberParam(params, "rate", 12), getNumberParam(params, "threshold", 8)),
    },
    {
      id: "isNoShowRateAboveThreshold",
      label: "isNoShowRateAboveThreshold",
      description: "Check if a no-show rate exceeds threshold.",
      params: [
        { key: "rate", label: "rate", type: "number", defaultValue: "18" },
        { key: "threshold", label: "threshold", type: "number", defaultValue: "20" },
      ],
      run: (params: Record<string, RawParamValue>): boolean =>
        isNoShowRateAboveThreshold(getNumberParam(params, "rate", 18), getNumberParam(params, "threshold", 20)),
    },
  ];
}

let cachedOperations: OperationDefinition[] | null = null;

export function buildOperations(): OperationDefinition[] {
  return buildOperationsBody();
}

export function getOperations(): OperationDefinition[] {
  if (!cachedOperations) {
    cachedOperations = buildOperations();
  }
  return cachedOperations;
}

export function defaultParamValues(operation: OperationDefinition): Record<string, RawParamValue> {
  const values: Record<string, RawParamValue> = {};
  operation.params.forEach((param) => {
    if (Array.isArray(param.defaultValue)) {
      values[param.key] = param.defaultValue;
      return;
    }
    values[param.key] = param.defaultValue ?? "";
  });
  return values;
}
