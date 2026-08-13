import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type {
  FeedbackRating,
  KnowledgeQueryResponse,
  KnowledgeSource,
  MemoryDecision,
  MemoryListItem,
  MemoryProposal,
} from "../types/knowledge";

type AgentQueryRaw = {
  answer: string;
  trace_id: string;
  sources: KnowledgeSource[];
  sources_used?: string[];
  memory_proposal?: MemoryProposal | null;
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
    memory_proposal: raw.memory_proposal ?? null,
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

export async function postMemoryDecision(input: {
  proposal_id: string;
  decision: MemoryDecision;
  edited_text?: string;
}): Promise<void> {
  const response = await healthcoreFetch("/agent/memory/decision", {
    method: "POST",
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error("memory decision failed");
  }
}

export async function listMemories(): Promise<{
  memories: MemoryListItem[];
  clinic_id: string;
}> {
  const response = await healthcoreFetch("/agent/memory");
  if (!response.ok) {
    throw new Error("memory list failed");
  }
  return (await response.json()) as { memories: MemoryListItem[]; clinic_id: string };
}

export async function deleteMemory(id: string): Promise<void> {
  const response = await healthcoreFetch(`/agent/memory/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("memory delete failed");
  }
}
