export type KnowledgeSource = {
  source_document: string;
  section: string;
  score: number;
};

export type KnowledgeQueryResponse = {
  query_id: string;
  answer: string;
  sources: KnowledgeSource[];
};

export type FeedbackRating = "up" | "down";
