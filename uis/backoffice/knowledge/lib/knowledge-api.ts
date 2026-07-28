import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type { FeedbackRating, KnowledgeQueryResponse, KnowledgeSource } from "../types/knowledge";

type AgentQueryRaw = {
  answer: string;
  trace_id: string;
  sources: KnowledgeSource[];
  sources_used?: string[];
};

export async function queryKnowledge(question: string): Promise<KnowledgeQueryResponse> {
  const response = await healthcoreFetch("/agent/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error("Something went wrong, please try again.");
  }
  const raw = (await response.json()) as AgentQueryRaw;
  return {
    query_id: raw.trace_id,
    answer: raw.answer,
    sources: raw.sources ?? [],
    sources_used: raw.sources_used,
  };
}

export async function submitFeedback(input: {
  query_id: string;
  rating: FeedbackRating;
  comment?: string;
}): Promise<void> {
  const response = await healthcoreFetch("/agent/feedback", {
    method: "POST",
    body: JSON.stringify({
      trace_id: input.query_id,
      rating: input.rating,
      comment: input.comment,
    }),
  });
  if (!response.ok) {
    throw new Error("feedback failed");
  }
}
