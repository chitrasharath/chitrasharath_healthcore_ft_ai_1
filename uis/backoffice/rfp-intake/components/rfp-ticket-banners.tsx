"use client";

import type { TicketDetail } from "../types/rfp-intake";

type Props = { detail: TicketDetail };

export const RfpTicketBanners = ({ detail }: Props) => {
  const needing = detail.sections_needing_review ?? 0;
  const sectionPhi = detail.sections.some(
    (s) => Boolean(s.evaluation_results?.contains_phi) || s.status === "needs_human_review",
  );
  return (
    <>
      {detail.job_status === "failed" ? (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-red-950">
          Job failed
          {detail.job_checkpoint ? ` at “${detail.job_checkpoint}”` : ""}.
          {detail.job_error ? ` ${detail.job_error}` : ""}
        </div>
      ) : null}
      {detail.metadata?.contains_phi || sectionPhi ? (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-amber-950">
          Flagged for Compliance (Claire Whitfield): PHI detected and redacted. Raw
          patient content is not shown.
        </div>
      ) : null}
      {needing > 0 ? (
        <div className="rounded border border-orange-300 bg-orange-50 px-3 py-2 text-orange-950">
          {needing} section(s) need human review. Other sections continue independently.
        </div>
      ) : null}
      {detail.phase2_complete ? (
        <div className="rounded border border-emerald-300 bg-emerald-50 px-3 py-2 text-emerald-950">
          Phase 2 complete — ticket remains under_evaluation until Part 3 approvals.
        </div>
      ) : null}
      {detail.needs_human_review && needing === 0 ? (
        <div className="rounded border border-sky-300 bg-sky-50 px-3 py-2 text-sky-950">
          Human review needed: {detail.classifier_reason || "Review required."}
        </div>
      ) : null}
      {detail.status === "discarded" ? (
        <div className="rounded border border-slate-300 bg-slate-50 px-3 py-2">
          Discarded: {detail.classifier_reason || "Not a HealthCore institutional RFP."}
        </div>
      ) : null}
    </>
  );
};
