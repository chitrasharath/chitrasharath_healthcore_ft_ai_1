"use client";

import type { TicketSummary } from "../types/rfp-intake";

type Props = {
  tickets: TicketSummary[];
  selectedId: string | null;
  onSelect: (ticketId: string) => void;
  onStartDraft?: (ticketId: string) => void;
  onDelete?: (ticketId: string) => void;
  draftingId?: string | null;
  busy?: boolean;
};

export const RfpTicketList = ({
  tickets,
  selectedId,
  onSelect,
  onStartDraft,
  onDelete,
  draftingId,
  busy,
}: Props) => (
  <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
    {tickets.length === 0 ? (
      <li className="px-4 py-6 text-sm text-slate-500">No tickets yet.</li>
    ) : (
      tickets.map((ticket) => (
        <li key={ticket.ticket_id} className="flex items-stretch gap-2 px-2 py-1">
          <button
            type="button"
            onClick={() => onSelect(ticket.ticket_id)}
            className={`flex flex-1 flex-col gap-1 px-2 py-2 text-left text-sm hover:bg-sky-50 ${
              selectedId === ticket.ticket_id ? "bg-sky-50" : ""
            }`}
          >
            <span className="font-medium text-slate-900">
              {ticket.client_name || ticket.rfp_id}
            </span>
            <span className="text-slate-600">
              {ticket.status}
              {ticket.status === "discarded" ? " · not an RFP" : ""}
              {ticket.job_status === "failed" ? " · job failed" : ""}
              {ticket.contains_phi ? " · PHI flagged" : ""}
              {(ticket.sections_needing_review ?? 0) > 0
                ? ` · ${ticket.sections_needing_review} need review`
                : ""}
            </span>
          </button>
          <div className="flex flex-col justify-center gap-1">
            {ticket.status === "intake_complete" && !ticket.from_run_all && onStartDraft ? (
              <button
                type="button"
                disabled={draftingId === ticket.ticket_id}
                className="whitespace-nowrap rounded bg-sky-700 px-2 py-1 text-xs text-white disabled:opacity-50"
                onClick={() => onStartDraft(ticket.ticket_id)}
              >
                Start drafting
              </button>
            ) : null}
            {onDelete ? (
              <button
                type="button"
                disabled={busy}
                className="whitespace-nowrap rounded border border-rose-300 px-2 py-1 text-xs text-rose-800 disabled:opacity-50"
                onClick={() => onDelete(ticket.ticket_id)}
              >
                Delete
              </button>
            ) : null}
          </div>
        </li>
      ))
    )}
  </ul>
);
