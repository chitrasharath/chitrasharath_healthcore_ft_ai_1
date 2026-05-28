import type { CandidateQueryState } from "@/components/candidate-list/types";

const DEFAULT_LIMIT = 10;
const readParam = (value: string | null): string => value ?? "";

export const toQuery = (params: URLSearchParams): CandidateQueryState => ({
  search: readParam(params.get("search")),
  status: readParam(params.get("status")),
  stage: readParam(params.get("stage")),
  created: readParam(params.get("created")),
  page: Number(params.get("page") ?? "1"),
  limit: Number(params.get("limit") ?? String(DEFAULT_LIMIT)),
  returnTo: buildReturnTo(params),
});

const buildReturnTo = (params: URLSearchParams) => {
  const next = new URLSearchParams(params.toString());
  next.delete("created");
  return `/?${next.toString()}`;
};

export const withParams = (search: URLSearchParams, mutate: (next: URLSearchParams) => void) => {
  const next = new URLSearchParams(search.toString());
  mutate(next);
  return `/?${next.toString()}`;
};