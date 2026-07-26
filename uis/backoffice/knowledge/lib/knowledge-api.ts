import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type { FeedbackRating, KnowledgeQueryResponse } from "../types/knowledge";

export async function queryKnowledge(question: string): Promise<KnowledgeQueryResponse> {
  const response = await healthcoreFetch("/knowledge/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error("Something went wrong, please try again.");
  }
  return (await response.json()) as KnowledgeQueryResponse;
}

export async function submitFeedback(input: {
  query_id: string;
  rating: FeedbackRating;
  comment?: string;
}): Promise<void> {
  const response = await healthcoreFetch("/knowledge/feedback", {
    method: "POST",
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error("feedback failed");
  }
}
