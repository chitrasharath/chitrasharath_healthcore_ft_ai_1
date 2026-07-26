import type { KnowledgeSource } from "../types/knowledge";

type Props = {
  sources: KnowledgeSource[];
};

export const KnowledgeSources = ({ sources }: Props) => {
  if (!sources.length) return null;
  return (
    <div className="mt-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Sources
      </h3>
      <ul className="mt-2 space-y-1 text-sm text-slate-700 dark:text-slate-200">
        {sources.map((source) => (
          <li key={`${source.source_document}-${source.section}-${source.score}`}>
            {source.source_document} · {source.section}
          </li>
        ))}
      </ul>
    </div>
  );
};
