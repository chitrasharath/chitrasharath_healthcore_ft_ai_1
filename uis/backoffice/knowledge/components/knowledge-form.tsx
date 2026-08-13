"use client";

type Props = {
  question: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
};

export const KnowledgeForm = ({ question, onChange, onSubmit, loading }: Props) => {
  const disabled = loading || !question.trim();
  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor="knowledge-question" className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
        Your question
      </label>
      <textarea
        id="knowledge-question"
        name="question"
        rows={4}
        value={question}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        placeholder="e.g. Is Medicaid accepted in Georgia?"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Searching…" : "Ask"}
      </button>
    </form>
  );
};
