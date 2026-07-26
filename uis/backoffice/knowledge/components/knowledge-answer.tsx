import type { KnowledgeQueryResponse } from "../types/knowledge";
import { KnowledgeFeedback } from "./knowledge-feedback";
import { KnowledgeSources } from "./knowledge-sources";

type Props = {
  result: KnowledgeQueryResponse;
};

export const KnowledgeAnswer = ({ result }: Props) => {
  const noSources = result.sources.length === 0;
  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900"
      aria-live="polite"
    >
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Answer
      </h2>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-900 dark:text-slate-100">
        {result.answer}
      </p>
      {noSources ? (
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          No matching sources in the knowledge base for this question.
        </p>
      ) : (
        <KnowledgeSources sources={result.sources} />
      )}
      <KnowledgeFeedback key={result.query_id} queryId={result.query_id} />
    </section>
  );
};
