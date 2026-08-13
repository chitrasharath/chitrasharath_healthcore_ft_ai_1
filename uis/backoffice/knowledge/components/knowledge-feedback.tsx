"use client";

import { useKnowledgeFeedback } from "../hooks/use-knowledge-feedback";

type Props = {
  queryId: string;
};

export const KnowledgeFeedback = ({ queryId }: Props) => {
  const { rating, comment, setComment, thanks, showComment, send, submitComment } =
    useKnowledgeFeedback(queryId);

  return (
    <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700">
      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Was this helpful?</p>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          aria-label="Thumbs up"
          aria-pressed={rating === "up"}
          onClick={() => void send("up")}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
        >
          👍
        </button>
        <button
          type="button"
          aria-label="Thumbs down"
          aria-pressed={rating === "down"}
          onClick={() => void send("down")}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
        >
          👎
        </button>
      </div>
      {showComment ? (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-amber-800 dark:text-amber-200">
            Do not include patient names or any personal health information.
          </p>
          <label htmlFor="feedback-comment" className="sr-only">
            Suggest a correction
          </label>
          <textarea
            id="feedback-comment"
            rows={2}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            placeholder="Optional: suggest a correction"
          />
          <button
            type="button"
            onClick={() => void submitComment()}
            className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-semibold text-white dark:bg-slate-200 dark:text-slate-900"
          >
            Send feedback
          </button>
        </div>
      ) : null}
      {thanks ? (
        <p className="mt-2 text-sm text-teal-700 dark:text-teal-300" role="status">
          Thanks for the feedback
        </p>
      ) : null}
    </div>
  );
};
