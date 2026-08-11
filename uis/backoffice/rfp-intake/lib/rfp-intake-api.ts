import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type { TicketDetail, TicketSummary, UploadAccepted } from "../types/rfp-intake";

export async function uploadRfpPdf(file: File): Promise<UploadAccepted> {
  const body = new FormData();
  body.append("file", file);
  let response: Response;
  try {
    response = await healthcoreFetch("/rfp-intake/uploads", {
      method: "POST",
      body,
    });
  } catch {
    throw new Error(
      "Could not reach the API. Is it running on :8000, and is NEXT_PUBLIC_API_URL correct?",
    );
  }
  if (!response.ok) {
    throw new Error(`Upload failed (${response.status}). Check the API logs.`);
  }
  return (await response.json()) as UploadAccepted;
}

export async function listTickets(): Promise<TicketSummary[]> {
  const response = await healthcoreFetch("/rfp-intake/tickets");
  if (!response.ok) {
    throw new Error("Could not load tickets.");
  }
  return (await response.json()) as TicketSummary[];
}

export async function getTicket(ticketId: string): Promise<TicketDetail> {
  const response = await healthcoreFetch(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}`);
  if (!response.ok) {
    throw new Error("Could not load ticket.");
  }
  return (await response.json()) as TicketDetail;
}

export async function rerunTicket(ticketId: string): Promise<UploadAccepted> {
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/rerun`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error("Re-run failed.");
  }
  return (await response.json()) as UploadAccepted;
}
