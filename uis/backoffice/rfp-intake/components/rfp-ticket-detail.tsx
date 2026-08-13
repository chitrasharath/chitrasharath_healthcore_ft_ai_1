"use client";

import type { TicketDetail } from "../types/rfp-intake";
import { RfpSectionPanel } from "./rfp-section-panel";
import { RfpTicketBanners } from "./rfp-ticket-banners";

type Props = {
  detail: TicketDetail;
  onStartDraft?: () => void;
  onContinueToApproval?: () => void;
  onRunPhase3?: () => void;
  onDownload?: () => void;
  onDelete?: () => void;
  onRedraft?: (departmentId: string) => void;
  onReleaseRedacted?: (departmentId: string) => void;
  onDecide?: (
    departmentId: string,
    decision: "approve" | "reject",
    approver: string,
    reason?: string,
  ) => void;
  drafting?: boolean;
  busy?: boolean;
  busyDept?: string | null;
  busyDepts?: string[];
};

export const RfpTicketDetail = ({
  detail,
  onStartDraft,
  onContinueToApproval,
  onRunPhase3,
  onDownload,
  onDelete,
  onRedraft,
  onReleaseRedacted,
  onDecide,
  drafting,
  busy,
  busyDept,
  busyDepts,
}: Props) => {
  const meta = detail.metadata;
  const canDraft =
    detail.status === "intake_complete" && !detail.from_run_all && onStartDraft;
  const canPhase3 =
    Boolean(detail.phase2_all_passed) &&
    detail.status === "under_evaluation" &&
    !detail.from_run_all &&
    onRunPhase3;
  const waiting = detail.status === "waiting_for_approval";
  const canDownload =
    detail.status === "done" && detail.final_document_available && onDownload;

  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-800">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-slate-900">
          {meta?.client_name || detail.rfp_id}
        </h2>
        <p className="text-slate-600">
          Status: <span className="font-medium">{detail.status}</span> · {detail.ticket_id}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {canDraft ? (
            <>
              <button
                type="button"
                disabled={drafting}
                onClick={() => onStartDraft?.()}
                className="rounded bg-sky-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
              >
                {drafting ? "Starting…" : "Start drafting"}
              </button>
              {onContinueToApproval ? (
                <button
                  type="button"
                  disabled={drafting}
                  onClick={() => onContinueToApproval()}
                  className="rounded border border-sky-700 px-3 py-1.5 text-sm text-sky-800 disabled:opacity-50"
                >
                  Draft + send for approval
                </button>
              ) : null}
            </>
          ) : null}
          {canPhase3 ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => onRunPhase3?.()}
              className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            >
              {busy ? "Starting…" : "Run Phase 3"}
            </button>
          ) : null}
          {canDownload ? (
            <button
              type="button"
              onClick={() => onDownload?.()}
              className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white"
            >
              Download final documents
            </button>
          ) : null}
          {onDelete ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => onDelete()}
              className="rounded border border-rose-400 px-3 py-1.5 text-sm text-rose-800 disabled:opacity-50"
            >
              {busy ? "Deleting…" : "Delete ticket"}
            </button>
          ) : null}
        </div>
      </header>
      <RfpTicketBanners detail={detail} />
      {detail.arbitration_records?.length ? (
        <div className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
          Latest arbitration: {detail.arbitration_records[0]?.trigger_id} —{" "}
          {detail.arbitration_records[0]?.arbiter}
        </div>
      ) : null}
      {meta ? (
        <dl className="grid gap-2 sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Program</dt>
            <dd>{meta.program_type || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Country</dt>
            <dd>{meta.client_country || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Population</dt>
            <dd>{meta.covered_population || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Departments</dt>
            <dd>{(meta.departments_needed || []).join(", ") || "—"}</dd>
          </div>
        </dl>
      ) : null}
      {detail.sections.map((section) => (
        <RfpSectionPanel
          key={section.department_id}
          section={section}
          waitingForApproval={waiting}
          busy={busy}
          busyDept={busyDept}
          busyDepts={busyDepts}
          onRedraft={onRedraft}
          onReleaseRedacted={onReleaseRedacted}
          onDecide={onDecide}
        />
      ))}
      {meta?.sales_summary ? (
        <section className="space-y-1">
          <h3 className="font-medium text-slate-900">What to ask whom</h3>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">
            {JSON.stringify(meta.sales_summary, null, 2)}
          </pre>
        </section>
      ) : null}
    </div>
  );
};
