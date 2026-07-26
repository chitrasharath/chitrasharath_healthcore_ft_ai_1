/** @jest-environment node */

const mockHealthcoreFetch = jest.fn();

jest.mock("@backoffice/shared/lib/healthcore-api", () => ({
  healthcoreFetch: (...args: unknown[]) => mockHealthcoreFetch(...args),
}));

describe("knowledge-api", () => {
  beforeEach(() => {
    mockHealthcoreFetch.mockReset();
  });

  it("queryKnowledge posts the question and returns JSON", async () => {
    mockHealthcoreFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        query_id: "q1",
        answer: "Fee is 50 USD",
        sources: [{ source_document: "appointment-policy", section: "Cancellation", score: 0.9 }],
      }),
    });

    const { queryKnowledge } = await import("@backoffice/knowledge/lib/knowledge-api");
    const result = await queryKnowledge("cancellation fee?");

    expect(mockHealthcoreFetch).toHaveBeenCalledWith("/knowledge/query", {
      method: "POST",
      body: JSON.stringify({ question: "cancellation fee?" }),
    });
    expect(result.answer).toContain("50 USD");
    expect(result.sources).toHaveLength(1);
  });

  it("queryKnowledge throws a friendly error on failure", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: false, status: 500 });
    const { queryKnowledge } = await import("@backoffice/knowledge/lib/knowledge-api");
    await expect(queryKnowledge("hi")).rejects.toThrow("Something went wrong");
  });

  it("submitFeedback posts rating with query_id", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: true });
    const { submitFeedback } = await import("@backoffice/knowledge/lib/knowledge-api");
    await submitFeedback({ query_id: "q1", rating: "down", comment: "unclear" });
    expect(mockHealthcoreFetch).toHaveBeenCalledWith("/knowledge/feedback", {
      method: "POST",
      body: JSON.stringify({ query_id: "q1", rating: "down", comment: "unclear" }),
    });
  });

  it("submitFeedback failure rejects without swallowing", async () => {
    mockHealthcoreFetch.mockResolvedValue({ ok: false, status: 500 });
    const { submitFeedback } = await import("@backoffice/knowledge/lib/knowledge-api");
    await expect(submitFeedback({ query_id: "q1", rating: "up" })).rejects.toThrow(
      "feedback failed",
    );
  });
});
