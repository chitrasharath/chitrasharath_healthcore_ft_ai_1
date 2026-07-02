import type {
  CandidateCreatePayload,
  CandidateListQuery,
  CandidateListResponse,
  CandidateNotesResponse,
  CandidatePatchPayload,
  CandidateReplacePayload,
  CandidateRecord,
  NoteCreatePayload,
} from "@backoffice/talent-tracker/types/candidate";

const BASE_URL =
  process.env.NEXT_PUBLIC_TRACKER_API_URL ?? "https://playground.4geeks.com/tracker/api/v1";

const NETWORK_ERROR_MESSAGE =
  "Unable to connect. Please check your connection and try again.";

const GENERIC_ERROR_MESSAGE = "Something went wrong. Please try again.";

const isNetworkFailure = (error: unknown): boolean =>
  error instanceof TypeError && error.message.toLowerCase().includes("fetch");

const TRACKER_API_MISCONFIG_MESSAGE =
  "Could not reach the talent tracker API. Check that NEXT_PUBLIC_TRACKER_API_URL is correct, then try again.";

const INVALID_CANDIDATE_MESSAGE = "Invalid candidate ID.";

const isRecordByIdPath = (path: string): boolean => /\/records\/[^/]+/.test(path);

const parseErrorPayload = (body: string): { detail?: string; error?: string } => {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown; error?: unknown };
    return {
      detail: typeof parsed.detail === "string" ? parsed.detail : undefined,
      error: typeof parsed.error === "string" ? parsed.error : undefined,
    };
  } catch {
    return {};
  }
};

const resolve404Message = (body: string, path: string): string => {
  const { detail, error } = parseErrorPayload(body);

  if (error?.toLowerCase().includes("record not found")) {
    return INVALID_CANDIDATE_MESSAGE;
  }

  if (detail?.trim().toLowerCase() === "not found") {
    return TRACKER_API_MISCONFIG_MESSAGE;
  }

  if (isRecordByIdPath(path)) {
    return INVALID_CANDIDATE_MESSAGE;
  }

  return TRACKER_API_MISCONFIG_MESSAGE;
};

const isUnhelpfulApiMessage = (message: string): boolean => {
  const lower = message.toLowerCase();
  return (
    lower === "not found" ||
    lower.includes("404") ||
    lower.includes("page not found") ||
    lower.includes("cannot get ")
  );
};

const sanitizeErrorBody = (body: string, status: number, path: string): string => {
  if (status === 404) {
    return resolve404Message(body, path);
  }

  const trimmed = body.trim();
  if (!trimmed) return GENERIC_ERROR_MESSAGE;

  const lower = trimmed.toLowerCase();
  if (lower.includes("<html") || lower.includes("<!doctype") || lower.includes("traceback")) {
    return GENERIC_ERROR_MESSAGE;
  }

  const { detail, error } = parseErrorPayload(trimmed);
  if (error?.trim()) {
    return error.toLowerCase().includes("record not found") ? INVALID_CANDIDATE_MESSAGE : error;
  }
  if (detail?.trim()) {
    return isUnhelpfulApiMessage(detail) ? TRACKER_API_MISCONFIG_MESSAGE : detail;
  }

  return isUnhelpfulApiMessage(trimmed) ? TRACKER_API_MISCONFIG_MESSAGE : GENERIC_ERROR_MESSAGE;
};

const buildUrl = (path: string, query?: CandidateListQuery) => {
  const url = new URL(`${BASE_URL}${path}`);

  if (query?.status) url.searchParams.set("status", query.status);
  if (query?.stage) url.searchParams.set("stage", query.stage);
  if (query?.search) url.searchParams.set("search", query.search);
  if (query?.page) url.searchParams.set("page", String(query.page));
  if (query?.limit) url.searchParams.set("limit", String(query.limit));

  return url.toString();
};

const fetchWithNetworkGuard = async (url: string, init: RequestInit = {}): Promise<Response> => {
  try {
    return await fetch(url, init);
  } catch (error) {
    if (isNetworkFailure(error)) {
      throw new Error(NETWORK_ERROR_MESSAGE);
    }
    throw error;
  }
};

const readResponse = async <T>(response: Response, path: string): Promise<T> => {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(sanitizeErrorBody(detail, response.status, path));
  }

  return (await response.json()) as T;
};

const requestJson = async <T>(path: string, init: RequestInit = {}, query?: CandidateListQuery) => {
  const response = await fetchWithNetworkGuard(buildUrl(path, query), init);
  return readResponse<T>(response, path);
};

const requestVoid = async (path: string, init: RequestInit = {}) => {
  const response = await fetchWithNetworkGuard(buildUrl(path), init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(sanitizeErrorBody(detail, response.status, path));
  }
};

export const getCandidates = async (
  query: CandidateListQuery,
): Promise<CandidateListResponse> => requestJson<CandidateListResponse>("/records", { cache: "no-store" }, query);

export const getCandidateById = async (id: string): Promise<CandidateRecord> =>
  requestJson<CandidateRecord>(`/records/${id}`, { cache: "no-store" });

export const patchCandidate = async (
  id: string,
  payload: CandidatePatchPayload,
): Promise<CandidateRecord> =>
  requestJson<CandidateRecord>(`/records/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const replaceCandidate = async (
  id: string,
  payload: CandidateReplacePayload,
): Promise<CandidateRecord> =>
  requestJson<CandidateRecord>(`/records/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const createCandidate = async (payload: CandidateCreatePayload): Promise<CandidateRecord> =>
  requestJson<CandidateRecord>("/records", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const getNotes = async (id: string): Promise<CandidateNotesResponse> =>
  requestJson<CandidateNotesResponse>(`/records/${id}/notes`, { cache: "no-store" });

export const createNote = async (id: string, payload: NoteCreatePayload): Promise<void> =>
  requestVoid(`/records/${id}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const deleteNote = async (id: string, noteId: string): Promise<void> =>
  requestVoid(`/records/${id}/notes/${noteId}`, { method: "DELETE" });

export const deleteCandidate = async (id: string): Promise<void> =>
  requestVoid(`/records/${id}`, { method: "DELETE" });
