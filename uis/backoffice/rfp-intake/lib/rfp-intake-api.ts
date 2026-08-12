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

export async function startDrafting(ticketId: string): Promise<{ ticket_id: string; status: string }> {
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/start-drafting`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Start drafting failed (${response.status}).`);
  }
  return (await response.json()) as { ticket_id: string; status: string };
}

export async function redraftSection(
  ticketId: string,
  departmentId: string,
): Promise<{ ticket_id: string; department_id: string; status: string }> {
  const qs = new URLSearchParams({ department_id: departmentId });
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/redraft?${qs}`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Re-draft failed (${response.status}).`);
  }
  return (await response.json()) as {
    ticket_id: string;
    department_id: string;
    status: string;
  };
}

export async function releaseRedactedSection(
  ticketId: string,
  departmentId: string,
): Promise<{ ticket_id: string; department_id: string; status: string; phi_cleared: boolean }> {
  const qs = new URLSearchParams({ department_id: departmentId });
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/release-redacted?${qs}`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Release redacted failed (${response.status}).`);
  }
  return (await response.json()) as {
    ticket_id: string;
    department_id: string;
    status: string;
    phi_cleared: boolean;
  };
}
