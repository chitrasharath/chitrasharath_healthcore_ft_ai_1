"use client";

import { useState } from "react";

import { queryKnowledge } from "../lib/knowledge-api";
import type { KnowledgeQueryResponse } from "../types/knowledge";

export const useKnowledgeQuery = () => {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KnowledgeQueryResponse | null>(null);

  const submit = async () => {
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await queryKnowledge(trimmed);
      setResult(data);
    } catch {
      setError("Something went wrong, please try again.");
    } finally {
      setLoading(false);
    }
  };

  return { question, setQuestion, loading, error, result, submit };
};
