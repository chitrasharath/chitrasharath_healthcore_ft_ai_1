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

export async function runAllFromPdf(file: File): Promise<UploadAccepted> {
  const body = new FormData();
  body.append("file", file);
  const response = await healthcoreFetch("/rfp-intake/run-all", {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error(`Run all failed (${response.status}).`);
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

export async function deleteTicket(ticketId: string): Promise<void> {
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}`,
    { method: "DELETE" },
  );
  if (!response.ok && response.status !== 204) {
    let detail = `Delete failed (${response.status}).`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
}

export async function startDrafting(
  ticketId: string,
  options?: { continueToApproval?: boolean },
): Promise<{ ticket_id: string; status: string }> {
  const qs = options?.continueToApproval ? "?continue_to_approval=true" : "";
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/start-drafting${qs}`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Start drafting failed (${response.status}).`);
  }
  return (await response.json()) as { ticket_id: string; status: string };
}

export async function sendForApproval(
  ticketId: string,
): Promise<{ ticket_id: string; status: string; message?: string }> {
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/send-for-approval`,
    { method: "POST" },
  );
  if (!response.ok) {
    let detail = `Run Phase 3 failed (${response.status}).`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as {
    ticket_id: string;
    status: string;
    message?: string;
  };
}

export async function submitDecision(
  ticketId: string,
  departmentId: string,
  body: { decision: "approve" | "reject"; approver: string; reason?: string },
): Promise<{ ticket_id: string; status: string; message?: string }> {
  const response = await healthcoreFetch(
    `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/departments/${encodeURIComponent(departmentId)}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!response.ok) {
    let detail = `Decision failed (${response.status}).`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as {
    ticket_id: string;
    status: string;
    message?: string;
  };
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
    let detail = `Re-draft failed (${response.status}).`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
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

export async function downloadFinalArtifacts(ticketId: string): Promise<void> {
  const downloads: { path: string; filename: string }[] = [
    {
      path: `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/final-document/markdown`,
      filename: `${ticketId}_final.md`,
    },
    {
      path: `/rfp-intake/tickets/${encodeURIComponent(ticketId)}/final-document/pdf`,
      filename: `${ticketId}_final.pdf`,
    },
  ];

  const failures: string[] = [];
  for (const { path, filename } of downloads) {
    const response = await healthcoreFetch(path, { method: "GET" });
    if (!response.ok) {
      failures.push(`${filename} (${response.status})`);
      continue;
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    // Give the browser a beat before the next download (popup blockers)
    await new Promise((r) => setTimeout(r, 150));
    URL.revokeObjectURL(objectUrl);
  }

  if (failures.length === downloads.length) {
    throw new Error(`Download failed: ${failures.join(", ")}`);
  }
  if (failures.length) {
    throw new Error(`Partial download failure: ${failures.join(", ")}`);
  }
}
