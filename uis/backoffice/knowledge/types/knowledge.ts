export type KnowledgeSource = {
  source_document: string;
  section: string;
  score: number;
};

export type MemoryProposal = {
  id: string;
  text: string;
  options: string[];
};

export type MemoryListItem = {
  id: string;
  type: "semantic" | "procedural";
  text: string;
  created_at: number;
  last_recalled_at: number;
  recall_count: number;
};

export type KnowledgeQueryResponse = {
  /** Alias of agent `trace_id` — kept for UI/feedback churn. */
  query_id: string;
  answer: string;
  sources: KnowledgeSource[];
  sources_used?: string[];
  memory_proposal?: MemoryProposal | null;
};

export type FeedbackRating = "up" | "down";

export type MemoryDecision = "approve" | "edit" | "reject";
