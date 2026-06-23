import type { CandidateQueryState } from "@backoffice/talent-tracker/components/candidate-list/types";
import { TALENT_TRACKER_HOME } from "@backoffice/talent-tracker/lib/paths";

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
  const query = next.toString();
  return query ? `${TALENT_TRACKER_HOME}?${query}` : TALENT_TRACKER_HOME;
};

export const withParams = (search: URLSearchParams, mutate: (next: URLSearchParams) => void) => {
  const next = new URLSearchParams(search.toString());
  mutate(next);
  const query = next.toString();
  return query ? `${TALENT_TRACKER_HOME}?${query}` : TALENT_TRACKER_HOME;
};
