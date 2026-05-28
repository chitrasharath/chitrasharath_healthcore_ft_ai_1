import { SaveIcon } from "@/components/icons";

type SaveCandidateBarProps = {
  submitting: boolean;
  onSubmit: () => void;
};

export const SaveCandidateBar = ({ submitting, onSubmit }: SaveCandidateBarProps) => {
  return (
    <div className="sticky bottom-20 mt-4 rounded-md border border-[var(--hc-border)] bg-white/95 p-3 backdrop-blur md:static md:border-0 md:bg-transparent md:p-0">
      <button
        type="button"
        onClick={onSubmit}
        disabled={submitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[var(--hc-brand)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50 md:w-auto"
      >
        <SaveIcon className="h-4 w-4" />
        {submitting ? "Saving..." : "Save Candidate"}
      </button>
    </div>
  );
};