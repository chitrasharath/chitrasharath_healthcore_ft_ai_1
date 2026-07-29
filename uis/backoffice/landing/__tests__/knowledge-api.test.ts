/** @jest-environment node */

const mockHealthcoreFetch = jest.fn();

jest.mock("@backoffice/shared/lib/healthcore-api", () => ({
  healthcoreFetch: (...args: unknown[]) => mockHealthcoreFetch(...args),
}));

describe("knowledge-api", () => {
  beforeEach(() => {
    mockHealthcoreFetch.mockReset();
  });

  it("queryKnowledge posts to /agent/query and maps trace_id to query_id", async () => {
    mockHealthcoreFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        trace_id: "run-abc123",
        answer: "Fee is 50 USD",
        sources: [{ source_document: "appointment-policy", section: "Cancellation", score: 0.9 }],
        sources_used: ["rag"],
      }),
    });

    const { queryKnowledge } = await import("@backoffice/knowledge/lib/knowledge-api");
    const result = await queryKnowledge("cancellation fee?");

    expect(mockHealthcoreFetch).toHaveBeenCalledWith("/agent/query", {
      method: "POST",
      body: JSON.stringify({ question: "cancellation fee?" }),
    });
    expect(result.query_id).toBe("run-abc123");
    expect(result.answer).toContain("50 USD");
    expect(result.sources).toHaveLength(1);
    expect(result.sources_used).toEqual(["rag"]);
  });

  it("queryKnowledge throws a friendly error on failure", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: false, status: 500 });
    const { queryKnowledge } = await import("@backoffice/knowledge/lib/knowledge-api");
    await expect(queryKnowledge("hi")).rejects.toThrow("Something went wrong");
  });

  it("submitFeedback posts to /agent/feedback with trace_id", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: true });
    const { submitFeedback } = await import("@backoffice/knowledge/lib/knowledge-api");
    await submitFeedback({ query_id: "run-abc123", rating: "down", comment: "unclear" });
    expect(mockHealthcoreFetch).toHaveBeenCalledWith("/agent/feedback", {
      method: "POST",
      body: JSON.stringify({
        trace_id: "run-abc123",
        rating: "down",
        comment: "unclear",
      }),
    });
  });

  it("submitFeedback failure rejects without swallowing", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: false, status: 500 });
    const { submitFeedback } = await import("@backoffice/knowledge/lib/knowledge-api");
    await expect(submitFeedback({ query_id: "q1", rating: "up" })).rejects.toThrow(
      "feedback failed",
    );
  });

  it("queryKnowledge maps memory_proposal when present", async () => {
    mockHealthcoreFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        trace_id: "run-mem",
        answer: "Noted.",
        sources: [],
        memory_proposal: {
          id: "mp-1",
          text: "Referrals fail Monday mornings",
          options: ["approve", "edit", "reject"],
        },
      }),
    });
    const { queryKnowledge } = await import("@backoffice/knowledge/lib/knowledge-api");
    const result = await queryKnowledge("referrals?");
    expect(result.memory_proposal?.id).toBe("mp-1");
    expect(result.memory_proposal?.text).toContain("Referrals");
  });

  it("postMemoryDecision posts approve payload", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: true });
    const { postMemoryDecision } = await import("@backoffice/knowledge/lib/knowledge-api");
    await postMemoryDecision({ proposal_id: "mp-1", decision: "approve" });
    expect(mockHealthcoreFetch).toHaveBeenCalledWith("/agent/memory/decision", {
      method: "POST",
      body: JSON.stringify({ proposal_id: "mp-1", decision: "approve" }),
    });
  });
});
