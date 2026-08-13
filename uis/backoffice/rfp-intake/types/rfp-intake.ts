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

export type ApprovalStatus = "pending" | "approved" | "request_changes";

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
  phase2_all_passed?: boolean;
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
  approval_status?: ApprovalStatus | string | null;
  approver?: string | null;
  approved_at?: string | null;
  approval_iteration?: number;
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
  phase2_all_passed?: boolean;
  approval_iterations_total?: number;
  final_document_available?: boolean;
  from_run_all?: boolean;
  created_at: string;
  updated_at: string;
  metadata: RfpMetadata | null;
  sections: DepartmentSection[];
  arbitration_records?: {
    trigger_id: string;
    arbiter: string;
    forced_action?: Record<string, unknown> | null;
    resolved?: boolean;
    created_at?: string | null;
  }[];
};

export type UploadAccepted = {
  ticket_id: string;
  rfp_id: string;
  status: string;
};

export const DEPARTMENT_OWNERS: Record<string, string> = {
  revenue: "Tom Callahan",
  clinical: "Dr. Marcus Reid",
  compliance: "Claire Whitfield",
};
