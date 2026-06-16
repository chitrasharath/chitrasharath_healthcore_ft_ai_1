import { COMPLIANCE_PROMPT_CATEGORIES, type Category } from "@/lib/categories";

type CompliancePromptProps = {
  categories: string[];
};

export const CompliancePrompt = ({ categories }: CompliancePromptProps) => {
  const needsPrompt = categories.some((c) =>
    COMPLIANCE_PROMPT_CATEGORIES.includes(c as Category),
  );
  if (!needsPrompt) return null;
  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
      <p className="font-semibold">Compliance agreement recommended</p>
      <p className="mt-1 text-sky-800">
        Technology-related suppliers should have a BAA or DPA recorded for Claire&apos;s audit trail.
      </p>
    </div>
  );
};
