"use client";

import type { TicketDetail } from "../types/rfp-intake";

type Props = { detail: TicketDetail };

export const RfpTicketBanners = ({ detail }: Props) => (
  <>
    {detail.job_status === "failed" ? (
      <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-red-950">
        Intake job failed
        {detail.job_checkpoint ? ` at checkpoint “${detail.job_checkpoint}”` : ""}.
        {detail.job_error ? ` ${detail.job_error}` : ""} Use Refresh, then re-upload or re-run.
      </div>
    ) : null}
    {detail.metadata?.contains_phi ? (
      <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-amber-950">
        Compliance review required: PHI was detected and redacted. Raw patient content is not shown.
      </div>
    ) : null}
    {detail.needs_human_review ? (
      <div className="rounded border border-sky-300 bg-sky-50 px-3 py-2 text-sky-950">
        Human review needed: {detail.classifier_reason || "Low classifier confidence."}
      </div>
    ) : null}
    {detail.status === "discarded" ? (
      <div className="rounded border border-slate-300 bg-slate-50 px-3 py-2">
        Discarded: {detail.classifier_reason || "Not a HealthCore institutional RFP."}
      </div>
    ) : null}
  </>
);
