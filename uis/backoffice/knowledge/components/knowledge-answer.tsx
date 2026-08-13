"use client";

import { useState } from "react";

import type { KnowledgeQueryResponse } from "../types/knowledge";
import { isGuardedAnswer } from "../lib/guarded-answer";
import { formatSourcesUsed } from "../lib/sources-used";
import { KnowledgeFeedback } from "./knowledge-feedback";
import { KnowledgeSources } from "./knowledge-sources";
import { MemoryConsentActions } from "./memory-consent-actions";

type Props = {
  result: KnowledgeQueryResponse;
  onProposalResolved?: () => void;
};

export const KnowledgeAnswer = ({ result, onProposalResolved }: Props) => {
  const [proposalGone, setProposalGone] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const toolLabels = formatSourcesUsed(result.sources_used);
  const hasRagSources = result.sources.length > 0;
  const guarded = isGuardedAnswer(result.answer, result.sources.length);
  const proposal = proposalGone ? null : result.memory_proposal;

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
      {statusMsg ? (
        <p className="mt-2 text-sm text-teal-800 dark:text-teal-300">{statusMsg}</p>
      ) : null}
      {proposal ? (
        <MemoryConsentActions
          proposal={proposal}
          onDone={(msg) => {
            setStatusMsg(msg);
            setProposalGone(true);
            onProposalResolved?.();
          }}
        />
      ) : null}
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
        </>
      )}
      <KnowledgeFeedback key={result.query_id} queryId={result.query_id} />
    </section>
  );
};
