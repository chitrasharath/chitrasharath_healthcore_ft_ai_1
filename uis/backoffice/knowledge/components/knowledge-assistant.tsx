"use client";

import { KnowledgeAnswer } from "./knowledge-answer";
import { KnowledgeForm } from "./knowledge-form";
import { KnowledgeHero } from "./knowledge-hero";
import { useKnowledgeQuery } from "../hooks/use-knowledge-query";

export const KnowledgeAssistant = () => {
  const { question, setQuestion, loading, error, result, submit } = useKnowledgeQuery();

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <KnowledgeHero />
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <KnowledgeForm
          question={question}
          onChange={setQuestion}
          onSubmit={() => void submit()}
          loading={loading}
        />
        {loading ? (
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400" role="status">
            Looking up clinic knowledge…
          </p>
        ) : null}
        {error ? (
          <p className="mt-4 text-sm text-red-700 dark:text-red-300" role="alert">
            {error}
          </p>
        ) : null}
      </div>
      {result ? <KnowledgeAnswer result={result} /> : null}
    </div>
  );
};
