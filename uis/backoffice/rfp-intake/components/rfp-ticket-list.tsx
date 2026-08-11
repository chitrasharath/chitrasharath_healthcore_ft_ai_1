"use client";

import type { TicketSummary } from "../types/rfp-intake";

type Props = {
  tickets: TicketSummary[];
  selectedId: string | null;
  onSelect: (ticketId: string) => void;
};

export const RfpTicketList = ({ tickets, selectedId, onSelect }: Props) => (
  <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
    {tickets.length === 0 ? (
      <li className="px-4 py-6 text-sm text-slate-500">No tickets yet.</li>
    ) : (
      tickets.map((ticket) => (
        <li key={ticket.ticket_id}>
          <button
            type="button"
            onClick={() => onSelect(ticket.ticket_id)}
            className={`flex w-full flex-col gap-1 px-4 py-3 text-left text-sm hover:bg-sky-50 ${
              selectedId === ticket.ticket_id ? "bg-sky-50" : ""
            }`}
          >
            <span className="font-medium text-slate-900">
              {ticket.client_name || ticket.rfp_id}
            </span>
            <span className="text-slate-600">
              {ticket.status}
              {ticket.job_status === "failed" ? " · job failed" : ""}
              {ticket.contains_phi ? " · PHI flagged" : ""}
              {ticket.needs_human_review ? " · Human review" : ""}
            </span>
          </button>
        </li>
      ))
    )}
  </ul>
);
