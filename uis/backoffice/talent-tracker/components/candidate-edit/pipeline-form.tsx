import type { CandidateStage, CandidateStatus } from "@backoffice/talent-tracker/types/candidate";

import { SaveIcon } from "@backoffice/talent-tracker/components/icons";

type PipelineFormProps = {
  status: CandidateStatus;
  stage: CandidateStage;
  saving: boolean;
  onStatusChange: (status: CandidateStatus) => void;
  onStageChange: (stage: CandidateStage) => void;
  onSave: () => void;
};

export const PipelineForm = ({
  status,
  stage,
  saving,
  onStatusChange,
  onStageChange,
  onSave,
}: PipelineFormProps) => {
  return (
    <section className="rounded-xl border border-[var(--hc-border)] bg-white p-4">
      <h2 className="mb-3 text-base font-semibold">Pipeline Updates</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <select value={status} onChange={(event) => onStatusChange(event.target.value as CandidateStatus)} className="rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm">
          <option value="received">Received</option>
          <option value="in_progress">In progress</option>
          <option value="selected">Selected</option>
          <option value="discarded">Discarded</option>
        </select>
        <select value={stage} onChange={(event) => onStageChange(event.target.value as CandidateStage)} className="rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm">
          <option value="pending">Pending</option>
          <option value="review">Review</option>
          <option value="personal_interview">Personal interview</option>
          <option value="technical_interview">Technical interview</option>
          <option value="offer_presented">Offer presented</option>
        </select>
      </div>
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="mt-3 inline-flex items-center gap-2 rounded-md bg-[var(--hc-brand)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        <SaveIcon className="h-4 w-4" />
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </section>
  );
};
