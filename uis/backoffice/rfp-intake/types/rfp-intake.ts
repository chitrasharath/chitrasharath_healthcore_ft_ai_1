export type TicketStatus = "analyzing" | "discarded" | "intake_complete";

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
  created_at: string;
  updated_at: string;
};

export type DepartmentSection = {
  department_id: string;
  key_aspects: string[] | Record<string, unknown> | null;
  evaluation_results: Record<string, unknown> | null;
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
