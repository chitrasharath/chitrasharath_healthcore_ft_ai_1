export type CandidateStatus =
  | "received"
  | "in_progress"
  | "selected"
  | "discarded";

export type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
  status: CandidateStatus;
  stage: CandidateStage;
  notes_count: number;
  applied_at: string;
};

export type CandidateNote = {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
};

export type CandidateListResponse = {
  total: number;
  page: number;
  limit: number;
  data: CandidateRecord[];
};

export type CandidateNotesResponse = {
  data: CandidateNote[];
  meta: {
    total: number;
  };
};

export type CandidateListQuery = {
  status?: CandidateStatus;
  stage?: CandidateStage;
  search?: string;
  page?: number;
  limit?: number;
};

export type CandidateCreatePayload = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
};

export type CandidateReplacePayload = CandidateCreatePayload;

export type CandidatePatchPayload = {
  status?: CandidateStatus;
  stage?: CandidateStage;
};

export type NoteCreatePayload = {
  content: string;
};
