import type {
  CandidateListResponse,
  CandidateRecord,
  CandidateStage,
  CandidateStatus,
} from "@/types/candidate";

export type CandidateQueryState = {
  search: string;
  status: string;
  stage: string;
  created: string;
  page: number;
  limit: number;
  returnTo: string;
};

export type CandidateListState = {
  result: CandidateListResponse | null;
  candidates: CandidateRecord[];
  loading: boolean;
  error: string;
  totalPages: number;
};

export type CandidateFilterValues = {
  search: string;
  status: CandidateStatus | "all";
  stage: CandidateStage | "all";
};
