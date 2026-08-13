"use client";

import { useEffect, useState } from "react";

import { submitFeedback } from "../lib/knowledge-api";
import type { FeedbackRating } from "../types/knowledge";

const THANKS_MS = 2500;

export const useKnowledgeFeedback = (queryId: string | null) => {
  const [rating, setRating] = useState<FeedbackRating | null>(null);
  const [comment, setComment] = useState("");
  const [thanks, setThanks] = useState(false);
  const [showComment, setShowComment] = useState(false);

  useEffect(() => {
    setRating(null);
    setComment("");
    setThanks(false);
    setShowComment(false);
  }, [queryId]);

  useEffect(() => {
    if (!thanks) return;
    const timer = window.setTimeout(() => {
      setThanks(false);
      setRating(null);
      setComment("");
      setShowComment(false);
    }, THANKS_MS);
    return () => window.clearTimeout(timer);
  }, [thanks]);

  const send = async (next: FeedbackRating) => {
    if (!queryId) return;
    setRating(next);
    setThanks(false);
    if (next === "down") {
      setShowComment(true);
      return;
    }
    setShowComment(false);
    try {
      await submitFeedback({ query_id: queryId, rating: next });
      setThanks(true);
    } catch {
      // fire-and-forget — keep answer visible
    }
  };

  const submitComment = async () => {
    if (!queryId || rating !== "down") return;
    try {
      await submitFeedback({
        query_id: queryId,
        rating: "down",
        comment: comment.trim() || undefined,
      });
      setThanks(true);
      setShowComment(false);
    } catch {
      // keep answer visible
    }
  };

  return {
    rating,
    comment,
    setComment,
    thanks,
    showComment,
    send,
    submitComment,
  };
};
