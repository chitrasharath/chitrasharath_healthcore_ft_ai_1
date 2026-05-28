import { Appointment, Claim, Clinician, Location } from "./types/models.js";
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
} from "./utils/transformations.js";
import {
  filterAppointmentsByStatus,
  filterClaims,
  groupClaimsBy,
  sortAppointmentsByDate,
  sortClaimsById,
} from "./utils/collections.js";
import { binarySearchClaimById, findClaimById, findClinicianById } from "./utils/search.js";
import {
  isDenialRateAboveThreshold,
  isNoShowRateAboveThreshold,
  validateClaim,
  validateClinician,
} from "./utils/validations.js";

const sampleLocations: Location[] = [
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

const sampleClaims: Claim[] = [
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

const sampleAppointments: Appointment[] = [
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

const sampleClinicians: Clinician[] = [
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

interface OperationResult {
  label: string;
  value: unknown;
}

type ParamInputType = "text" | "number" | "date" | "select" | "multiselect";
type RawParamValue = string | string[];

interface ParamOption {
  label: string;
  value: string;
}

interface ParameterDefinition {
  key: string;
  label: string;
  type: ParamInputType;
  options?: ParamOption[];
  placeholder?: string;
  defaultValue?: string | string[];
}

interface OperationDefinition {
  id: string;
  label: string;
  description: string;
  params: ParameterDefinition[];
  run: (params: Record<string, RawParamValue>) => unknown;
}

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

function buildOperations(): OperationDefinition[] {
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

const operations: OperationDefinition[] = buildOperations();
const executionHistory: OperationResult[] = [];

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function getRequiredElement<T extends HTMLElement>(id: string): T {
  const element: HTMLElement | null = document.getElementById(id);
  if (!element) {
    throw new Error(`Missing required element: ${id}`);
  }

  return element as T;
}

function currentOperation(): OperationDefinition {
  const select: HTMLSelectElement = getRequiredElement<HTMLSelectElement>("function-select");
  const selected: OperationDefinition | undefined = operations.find((operation: OperationDefinition) => operation.id === select.value);

  return selected ?? operations[0];
}

function controlId(operationId: string, paramKey: string): string {
  return `param-${operationId}-${paramKey}`;
}

function renderFunctionSelect(): void {
  const select: HTMLSelectElement = getRequiredElement<HTMLSelectElement>("function-select");
  select.innerHTML = operations
    .map((operation: OperationDefinition) => `<option value="${operation.id}">${operation.label}</option>`)
    .join("");

  if (operations.length > 0) {
    select.value = operations[0].id;
  }
}

function renderParamControls(operation: OperationDefinition): void {
  const description: HTMLElement = getRequiredElement<HTMLElement>("function-description");
  const paramsContainer: HTMLElement = getRequiredElement<HTMLElement>("param-controls");

  description.textContent = operation.description;

  if (operation.params.length === 0) {
    paramsContainer.innerHTML = `<p class="text-sm text-slate-600">This function uses only the sample data and has no configurable parameters.</p>`;
    return;
  }

  paramsContainer.innerHTML = operation.params
    .map((param: ParameterDefinition) => {
      const inputId: string = controlId(operation.id, param.key);

      if (param.type === "select") {
        const optionsHtml: string = (param.options ?? [])
          .map((option: ParamOption) => {
            const selected: boolean = option.value === param.defaultValue;
            return `<option value="${option.value}"${selected ? " selected" : ""}>${option.label}</option>`;
          })
          .join("");

        return `<label class="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">${param.label}
          <select id="${inputId}" data-param-key="${param.key}" data-param-type="${param.type}" class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">${optionsHtml}</select>
        </label>`;
      }

      if (param.type === "multiselect") {
        const defaultValues: string[] = Array.isArray(param.defaultValue) ? param.defaultValue : [];
        const optionsHtml: string = (param.options ?? [])
          .map((option: ParamOption) => {
            const selected: boolean = defaultValues.includes(option.value);
            return `<option value="${option.value}"${selected ? " selected" : ""}>${option.label}</option>`;
          })
          .join("");

        return `<label class="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">${param.label}
          <select id="${inputId}" data-param-key="${param.key}" data-param-type="${param.type}" multiple size="5" class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">${optionsHtml}</select>
        </label>`;
      }

      const value: string = Array.isArray(param.defaultValue)
        ? ""
        : (param.defaultValue ?? "");

      return `<label class="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">${param.label}
        <input id="${inputId}" data-param-key="${param.key}" data-param-type="${param.type}" type="${param.type}" value="${value}" placeholder="${param.placeholder ?? ""}" class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </label>`;
    })
    .join("");
}

function readParamValues(operation: OperationDefinition): Record<string, RawParamValue> {
  const values: Record<string, RawParamValue> = {};

  operation.params.forEach((param: ParameterDefinition) => {
    const inputId: string = controlId(operation.id, param.key);
    const element: HTMLElement = getRequiredElement<HTMLElement>(inputId);

    if (param.type === "multiselect") {
      const select: HTMLSelectElement = element as HTMLSelectElement;
      values[param.key] = Array.from(select.selectedOptions).map((option: HTMLOptionElement) => option.value);
      return;
    }

    if (param.type === "select") {
      values[param.key] = (element as HTMLSelectElement).value;
      return;
    }

    values[param.key] = (element as HTMLInputElement).value;
  });

  return values;
}

function defaultParamValues(operation: OperationDefinition): Record<string, RawParamValue> {
  const values: Record<string, RawParamValue> = {};

  operation.params.forEach((param: ParameterDefinition) => {
    if (Array.isArray(param.defaultValue)) {
      values[param.key] = param.defaultValue;
      return;
    }

    values[param.key] = param.defaultValue ?? "";
  });

  return values;
}

function updateLatestResult(result: OperationResult): void {
  const labelElement: HTMLElement = getRequiredElement<HTMLElement>("result-label");
  const outputElement: HTMLElement = getRequiredElement<HTMLElement>("result-output");

  labelElement.textContent = result.label;
  outputElement.textContent = formatJson(result.value);
}

function renderHistory(): void {
  const historyElement: HTMLElement = getRequiredElement<HTMLElement>("result-history");
  historyElement.innerHTML = executionHistory
    .slice()
    .reverse()
    .map(
      (entry: OperationResult, index: number) =>
        `<li class="rounded-lg border border-slate-200 bg-slate-50 p-2"><span class="font-semibold text-slate-900">${executionHistory.length - index}. ${entry.label}</span></li>`
    )
    .join("");
}

function executeOperation(operation: OperationDefinition, params: Record<string, RawParamValue>): void {
  const parameterSuffix: string = Object.keys(params).length === 0 ? "" : ` | params=${formatJson(params)}`;
  const result: OperationResult = {
    label: `${operation.label}${parameterSuffix}`,
    value: operation.run(params),
  };

  executionHistory.push(result);
  updateLatestResult(result);
  renderHistory();
  console.log(result.label, result.value);
}

function executeSelectedOperation(): void {
  const operation: OperationDefinition = currentOperation();
  const params: Record<string, RawParamValue> = readParamValues(operation);
  executeOperation(operation, params);
}

function executeAllOperations(): void {
  operations.forEach((operation: OperationDefinition) => {
    executeOperation(operation, defaultParamValues(operation));
  });
}

function clearOutput(): void {
  executionHistory.length = 0;
  getRequiredElement<HTMLElement>("result-label").textContent = "No operation executed yet.";
  getRequiredElement<HTMLElement>("result-output").textContent = "{}";
  getRequiredElement<HTMLElement>("result-history").innerHTML = "";
}

function wireControls(): void {
  const select: HTMLSelectElement = getRequiredElement<HTMLSelectElement>("function-select");
  const runSelectedButton: HTMLButtonElement = getRequiredElement<HTMLButtonElement>("run-selected");
  const runAllButton: HTMLButtonElement = getRequiredElement<HTMLButtonElement>("run-all");
  const clearButton: HTMLButtonElement = getRequiredElement<HTMLButtonElement>("clear-output");

  select.addEventListener("change", () => {
    renderParamControls(currentOperation());
  });

  runSelectedButton.addEventListener("click", executeSelectedOperation);
  runAllButton.addEventListener("click", executeAllOperations);
  clearButton.addEventListener("click", clearOutput);
}

function bootstrapUi(): void {
  if (typeof document === "undefined") {
    return;
  }

  try {
    renderFunctionSelect();
    renderParamControls(currentOperation());
    wireControls();
    clearOutput();
  } catch (error) {
    const message: string = error instanceof Error ? error.message : "Unknown initialization error";
    const description: HTMLElement | null = document.getElementById("function-description");
    const resultLabel: HTMLElement | null = document.getElementById("result-label");

    if (description) {
      description.textContent = `Initialization failed: ${message}`;
    }

    if (resultLabel) {
      resultLabel.textContent = `Initialization failed: ${message}`;
    }

    console.error("UI bootstrap failed", error);
  }
}

function runCliDemo(): void {
  const cliResults: OperationResult[] = operations.map((operation: OperationDefinition) => ({
    label: `${operation.label} | params=${formatJson(defaultParamValues(operation))}`,
    value: operation.run(defaultParamValues(operation)),
  }));

  console.log("HealthCore Milestone 2 CLI runner");
  console.log("===================================");
  for (let index: number = 0; index < cliResults.length; index += 1) {
    const result: OperationResult = cliResults[index];
    console.log("");
    console.log(`Function ${index + 1}: ${result.label}`);
    console.log("-----------------------------------");
    console.log(formatJson(result.value));
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrapUi);
  } else {
    bootstrapUi();
  }
} else {
  runCliDemo();
}
