import type {
  CandidateCreatePayload,
  CandidateListQuery,
  CandidateListResponse,
  CandidateNotesResponse,
  CandidatePatchPayload,
  CandidateReplacePayload,
  CandidateRecord,
  NoteCreatePayload,
} from "@/types/candidate";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!BASE_URL) {
  throw new Error("Missing NEXT_PUBLIC_API_URL environment variable.");
}

const buildUrl = (path: string, query?: CandidateListQuery) => {
  const url = new URL(`${BASE_URL}${path}`);

  if (query?.status) url.searchParams.set("status", query.status);
  if (query?.stage) url.searchParams.set("stage", query.stage);
  if (query?.search) url.searchParams.set("search", query.search);
  if (query?.page) url.searchParams.set("page", String(query.page));
  if (query?.limit) url.searchParams.set("limit", String(query.limit));

  return url.toString();
};

const readResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "API request failed.");
  }

  return (await response.json()) as T;
};

const requestJson = async <T>(path: string, init: RequestInit = {}, query?: CandidateListQuery) => {
  const response = await fetch(buildUrl(path, query), init);
  return readResponse<T>(response);
};

const requestVoid = async (path: string, init: RequestInit = {}) => {
  const response = await fetch(buildUrl(path), init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "API request failed.");
  }
};

export const getCandidates = async (
  query: CandidateListQuery,
): Promise<CandidateListResponse> => requestJson<CandidateListResponse>("/records", { cache: "no-store" }, query);

export const getCandidateById = async (id: string): Promise<CandidateRecord> => requestJson<CandidateRecord>(`/records/${id}`, { cache: "no-store" });

export const patchCandidate = async (
  id: string,
  payload: CandidatePatchPayload,
): Promise<CandidateRecord> => requestJson<CandidateRecord>(`/records/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

export const replaceCandidate = async (
  id: string,
  payload: CandidateReplacePayload,
): Promise<CandidateRecord> => requestJson<CandidateRecord>(`/records/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

export const createCandidate = async (
  payload: CandidateCreatePayload,
): Promise<CandidateRecord> => requestJson<CandidateRecord>("/records", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

export const getNotes = async (id: string): Promise<CandidateNotesResponse> => requestJson<CandidateNotesResponse>(`/records/${id}/notes`, { cache: "no-store" });

export const createNote = async (
  id: string,
  payload: NoteCreatePayload,
): Promise<void> => requestVoid(`/records/${id}/notes`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

export const deleteNote = async (id: string, noteId: string): Promise<void> => requestVoid(`/records/${id}/notes/${noteId}`, { method: "DELETE" });

export const deleteCandidate = async (id: string): Promise<void> => requestVoid(`/records/${id}`, { method: "DELETE" });
