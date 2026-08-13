"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  deleteTicket,
  downloadFinalArtifacts,
  getTicket,
  listTickets,
  redraftSection,
  releaseRedactedSection,
  rerunTicket,
  runAllFromPdf,
  sendForApproval,
  startDrafting,
  submitDecision,
  uploadRfpPdf,
} from "../lib/rfp-intake-api";
import type { TicketDetail, TicketSummary } from "../types/rfp-intake";

const POLL_MS = 3000;

const isActive = (status: string, jobStatus?: string | null, review?: boolean) => {
  if (jobStatus === "failed") return false;
  if (status === "analyzing" && !review) return true;
  if (status === "waiting_for_approval") return true;
  return status === "drafting" || status === "under_evaluation";
};

export function useRfpIntake() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [busyDept, setBusyDept] = useState<string | null>(null);
  const [busyDepts, setBusyDepts] = useState<string[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const autoDownloaded = useRef<Set<string>>(new Set());
  const autoPhase3 = useRef<Set<string>>(new Set());

  const refreshList = useCallback(async () => {
    setTickets(await listTickets());
  }, []);

  const refreshDetail = useCallback(async (ticketId: string) => {
    setDetail(await getTicket(ticketId));
  }, []);

  useEffect(() => {
    void refreshList().catch((err: Error) => setError(err.message));
  }, [refreshList]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    void refreshDetail(selectedId).catch((err: Error) => setError(err.message));
  }, [selectedId, refreshDetail]);

  useEffect(() => {
    const listActive = tickets.some((t) =>
      isActive(t.status, t.job_status, t.needs_human_review),
    );
    const detailActive = detail
      ? isActive(detail.status, detail.job_status, detail.needs_human_review)
      : false;
    if (!listActive && !detailActive) return;
    const id = window.setInterval(() => {
      void refreshList().catch(() => undefined);
      if (selectedId) void refreshDetail(selectedId).catch(() => undefined);
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [tickets, detail, selectedId, refreshList, refreshDetail]);

  useEffect(() => {
    if (!detail || detail.status !== "done" || !detail.final_document_available) return;
    if (autoDownloaded.current.has(detail.ticket_id)) return;
    autoDownloaded.current.add(detail.ticket_id);
    void downloadFinalArtifacts(detail.ticket_id).catch(() => undefined);
  }, [detail]);

  // Run-all: once every section is passed, start Phase 3 without a button click
  useEffect(() => {
    if (!detail?.from_run_all) return;
    if (detail.status === "analyzing" || detail.status === "intake_complete") {
      // Allow a later Phase 3 auto-start after a fresh intake / re-run
      autoPhase3.current.delete(detail.ticket_id);
      return;
    }
    if (!detail.phase2_all_passed) return;
    if (detail.status !== "under_evaluation" && detail.status !== "drafting") return;
    if (autoPhase3.current.has(detail.ticket_id)) return;
    autoPhase3.current.add(detail.ticket_id);
    setStatusMessage("Phase 2 complete — starting Phase 3 approvals…");
    void (async () => {
      try {
        await sendForApproval(detail.ticket_id);
        await refreshList();
        await refreshDetail(detail.ticket_id);
        setStatusMessage("Phase 3 started — waiting for department approvals.");
      } catch (err) {
        autoPhase3.current.delete(detail.ticket_id);
        setError(err instanceof Error ? err.message : "Auto Phase 3 failed");
        setStatusMessage(null);
      }
    })();
  }, [detail, refreshList, refreshDetail]);

  const refreshAll = useCallback(async () => {
    setError(null);
    try {
      await refreshList();
      if (selectedId) await refreshDetail(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    }
  }, [refreshList, refreshDetail, selectedId]);

  const upload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const accepted = await uploadRfpPdf(file);
      setSelectedId(accepted.ticket_id);
      await refreshList();
      await refreshDetail(accepted.ticket_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const runAll = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const accepted = await runAllFromPdf(file);
      setSelectedId(accepted.ticket_id);
      await refreshList();
      await refreshDetail(accepted.ticket_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run all failed");
    } finally {
      setUploading(false);
    }
  };

  const rerun = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setStatusMessage("Re-running intake…");
    try {
      await rerunTicket(selectedId);
      await refreshAll();
      setStatusMessage("Intake re-run queued.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Re-run failed");
    } finally {
      setBusy(false);
    }
  };

  const startDraft = async (ticketId?: string, continueToApproval = false) => {
    const id = ticketId || selectedId;
    if (!id) return;
    setDrafting(true);
    setError(null);
    setStatusMessage(
      continueToApproval ? "Drafting and sending for approval…" : "Starting drafting…",
    );
    try {
      setSelectedId(id);
      await startDrafting(id, { continueToApproval });
      await refreshList();
      await refreshDetail(id);
      setStatusMessage(
        continueToApproval ? "Draft + approval queued." : "Drafting queued.",
      );
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Start drafting failed");
    } finally {
      setDrafting(false);
    }
  };

  const runPhase3 = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setStatusMessage("Starting Phase 3 approvals…");
    try {
      const result = await sendForApproval(selectedId);
      await refreshAll();
      setStatusMessage(
        result.message === "already in approval"
          ? "Already waiting for approvals."
          : "Phase 3 started — waiting for approvals.",
      );
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Run Phase 3 failed");
    } finally {
      setBusy(false);
    }
  };

  const decide = async (
    departmentId: string,
    decision: "approve" | "reject",
    approver: string,
    reason?: string,
  ) => {
    if (!selectedId) return;
    setBusy(true);
    setBusyDept(departmentId);
    setError(null);
    setStatusMessage(
      decision === "approve"
        ? `Approving ${departmentId}…`
        : `Rejecting ${departmentId}…`,
    );
    try {
      await submitDecision(selectedId, departmentId, { decision, approver, reason });
      await refreshAll();
      setStatusMessage(
        decision === "approve"
          ? `${departmentId} approved.`
          : `${departmentId} rejected — revision queued.`,
      );
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusy(false);
      setBusyDept(null);
    }
  };

  const redraft = async (departmentId: string) => {
    if (!selectedId) return;
    if (busyDepts.includes(departmentId)) {
      setStatusMessage(`Already re-drafting ${departmentId}…`);
      return;
    }
    setBusyDepts((prev) => [...prev, departmentId]);
    setError(null);
    setStatusMessage(`Re-drafting ${departmentId}…`);
    try {
      await redraftSection(selectedId, departmentId);
      await refreshAll();
      setStatusMessage(`Re-draft started for ${departmentId}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-draft failed");
      setStatusMessage(null);
    } finally {
      setBusyDepts((prev) => prev.filter((d) => d !== departmentId));
    }
  };

  const releaseRedacted = async (departmentId: string) => {
    if (!selectedId) return;
    if (busyDepts.includes(departmentId)) {
      setStatusMessage(`${departmentId} is busy — try again in a moment.`);
      return;
    }
    setBusyDepts((prev) => [...prev, departmentId]);
    setError(null);
    setStatusMessage(`Redacting PHI for ${departmentId}…`);
    try {
      await releaseRedactedSection(selectedId, departmentId);
      await refreshAll();
      setStatusMessage(`PHI redacted for ${departmentId}.`);
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Release redacted failed");
    } finally {
      setBusyDepts((prev) => prev.filter((d) => d !== departmentId));
    }
  };

  const downloadDocs = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setStatusMessage("Downloading final documents…");
    try {
      await downloadFinalArtifacts(selectedId);
      setStatusMessage("Download started.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setBusy(false);
    }
  };

  const removeTicket = async (ticketId?: string) => {
    const id = ticketId || selectedId;
    if (!id) return;
    const label =
      tickets.find((t) => t.ticket_id === id)?.client_name ||
      detail?.metadata?.client_name ||
      id;
    if (
      typeof window !== "undefined" &&
      !window.confirm(`Delete ticket “${label}”? This cannot be undone.`)
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setStatusMessage("Deleting ticket…");
    try {
      await deleteTicket(id);
      if (selectedId === id) {
        setSelectedId(null);
        setDetail(null);
      }
      await refreshList();
      setStatusMessage("Ticket deleted.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  return {
    tickets,
    selectedId,
    setSelectedId,
    detail,
    error,
    statusMessage,
    uploading,
    drafting,
    busy,
    busyDept,
    busyDepts,
    upload,
    runAll,
    refreshAll,
    rerun,
    startDraft,
    runPhase3,
    decide,
    redraft,
    releaseRedacted,
    downloadDocs,
    removeTicket,
  };
}
