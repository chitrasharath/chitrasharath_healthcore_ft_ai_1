export type KnowledgeSource = {
  source_document: string;
  section: string;
  score: number;
};

export type KnowledgeQueryResponse = {
  /** Alias of agent `trace_id` — kept for UI/feedback churn. */
  query_id: string;
  answer: string;
  sources: KnowledgeSource[];
  sources_used?: string[];
};

export type FeedbackRating = "up" | "down";
