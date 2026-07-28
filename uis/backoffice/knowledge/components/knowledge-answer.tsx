import type { KnowledgeQueryResponse } from "../types/knowledge";
import { isGuardedAnswer } from "../lib/guarded-answer";
import { formatSourcesUsed } from "../lib/sources-used";
import { KnowledgeFeedback } from "./knowledge-feedback";
import { KnowledgeSources } from "./knowledge-sources";

type Props = {
  result: KnowledgeQueryResponse;
};

export const KnowledgeAnswer = ({ result }: Props) => {
  const toolLabels = formatSourcesUsed(result.sources_used);
  const hasRagSources = result.sources.length > 0;
  const guarded = isGuardedAnswer(result.answer, result.sources.length);
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
      {guarded ? (
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          This reply was limited by safety rules.
        </p>
      ) : (
        <>
          {hasRagSources ? <KnowledgeSources sources={result.sources} /> : null}
          {toolLabels.length > 0 ? (
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
              From {toolLabels.join(" · ")}
            </p>
          ) : null}
          {!hasRagSources && toolLabels.length === 0 ? (
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
              No matching sources in the knowledge base for this question.
            </p>
          ) : null}
        </>
      )}
      <KnowledgeFeedback key={result.query_id} queryId={result.query_id} />
    </section>
  );
};
