"use client";

import type { TicketDetail } from "../types/rfp-intake";
import { RfpSectionPanel } from "./rfp-section-panel";
import { RfpTicketBanners } from "./rfp-ticket-banners";

type Props = {
  detail: TicketDetail;
  onStartDraft?: () => void;
  onRedraft?: (departmentId: string) => void;
  onReleaseRedacted?: (departmentId: string) => void;
  drafting?: boolean;
  busyDepts?: string[];
};

export const RfpTicketDetail = ({
  detail,
  onStartDraft,
  onRedraft,
  onReleaseRedacted,
  drafting,
  busyDepts,
}: Props) => {
  const meta = detail.metadata;
  const canDraft = detail.status === "intake_complete" && onStartDraft;

  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-800">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-slate-900">
          {meta?.client_name || detail.rfp_id}
        </h2>
        <p className="text-slate-600">
          Status: <span className="font-medium">{detail.status}</span> · {detail.ticket_id}
        </p>
        {canDraft ? (
          <button
            type="button"
            disabled={drafting}
            onClick={() => onStartDraft?.()}
            className="mt-2 rounded bg-sky-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            {drafting ? "Starting…" : "Start drafting"}
          </button>
        ) : null}
      </header>
      <RfpTicketBanners detail={detail} />
      {meta ? (
        <dl className="grid gap-2 sm:grid-cols-2">
          <div><dt className="text-slate-500">Program</dt><dd>{meta.program_type || "—"}</dd></div>
          <div><dt className="text-slate-500">Country</dt><dd>{meta.client_country || "—"}</dd></div>
          <div><dt className="text-slate-500">Population</dt><dd>{meta.covered_population || "—"}</dd></div>
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
          busyDepts={busyDepts}
          onRedraft={onRedraft}
          onReleaseRedacted={onReleaseRedacted}
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
