export type TicketStatus =
  | "analyzing"
  | "discarded"
  | "intake_complete"
  | "drafting"
  | "under_evaluation"
  | "waiting_for_approval"
  | "done";

export type SectionStatus =
  | "drafting"
  | "under_evaluation"
  | "passed"
  | "needs_human_review";

export type TicketSummary = {
  ticket_id: string;
  rfp_id: string;
  status: TicketStatus | string;
  client_name: string | null;
  program_type: string | null;
  departments_needed: string[] | null;
  contains_phi: boolean;
  needs_human_review: boolean;
  job_status?: string | null;
  sections_needing_review?: number;
  phase2_complete?: boolean;
  created_at: string;
  updated_at: string;
};

export type EvaluationResult = {
  id: number;
  department_id: string;
  iteration: number;
  readability: Record<string, unknown> | null;
  relevance: Record<string, unknown> | null;
  compliance: Record<string, unknown> | null;
  contains_phi: boolean;
  overall_pass: boolean;
  feedback_for_generator: string | null;
  created_at: string;
};

export type DepartmentSection = {
  department_id: string;
  key_aspects: string[] | Record<string, unknown> | null;
  draft_content?: string | null;
  evaluation_results: Record<string, unknown> | null;
  status?: SectionStatus | string | null;
  iteration?: number;
  latest_evaluation_id?: number | null;
  evaluation_history?: EvaluationResult[];
};

export type RfpMetadata = {
  client_name: string | null;
  client_country: string | null;
  program_type: string | null;
  covered_population: string | null;
  covered_population_n: number | null;
  deadline: string | null;
  budget_range: string | null;
  departments_needed: string[] | null;
  readability_metrics: Record<string, unknown> | null;
  open_questions: string[] | null;
  contains_phi: boolean;
  sales_summary: Record<string, unknown> | null;
  classifier_result: Record<string, unknown> | null;
  markdown_preview: string | null;
};

export type TicketDetail = {
  ticket_id: string;
  rfp_id: string;
  status: TicketStatus | string;
  needs_human_review: boolean;
  classifier_reason: string | null;
  job_status?: string | null;
  job_checkpoint?: string | null;
  job_error?: string | null;
  sections_needing_review?: number;
  phase2_complete?: boolean;
  created_at: string;
  updated_at: string;
  metadata: RfpMetadata | null;
  sections: DepartmentSection[];
};

export type UploadAccepted = {
  ticket_id: string;
  rfp_id: string;
  status: string;
};
