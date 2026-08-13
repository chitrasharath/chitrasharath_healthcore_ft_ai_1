"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getTicket,
  listTickets,
  redraftSection,
  releaseRedactedSection,
  rerunTicket,
  startDrafting,
  uploadRfpPdf,
} from "../lib/rfp-intake-api";
import type { TicketDetail, TicketSummary } from "../types/rfp-intake";

const POLL_MS = 3000;

const isActive = (status: string, jobStatus?: string | null, review?: boolean) => {
  if (jobStatus === "failed") return false;
  if (status === "analyzing" && !review) return true;
  return status === "drafting" || status === "under_evaluation";
};

export function useRfpIntake() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [selectedId, setSelectedIdState] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [busyDepts, setBusyDepts] = useState<string[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const statusClearTimer = useRef<number | null>(null);

  const cancelStatusTimer = useCallback(() => {
    if (statusClearTimer.current != null) {
      window.clearTimeout(statusClearTimer.current);
      statusClearTimer.current = null;
    }
  }, []);

  const beginAction = useCallback(
    (message: string) => {
      cancelStatusTimer();
      setError(null);
      setStatusMessage(message);
    },
    [cancelStatusTimer],
  );

  const clearBoard = useCallback(() => {
    cancelStatusTimer();
    setError(null);
    setStatusMessage(null);
  }, [cancelStatusTimer]);

  const flashStatus = useCallback(
    (message: string, clearAfterMs = 3000) => {
      cancelStatusTimer();
      setError(null);
      setStatusMessage(message);
      statusClearTimer.current = window.setTimeout(() => {
        setStatusMessage(null);
        statusClearTimer.current = null;
      }, clearAfterMs);
    },
    [cancelStatusTimer],
  );

  const setSelectedId = useCallback(
    (id: string | null) => {
      clearBoard();
      setSelectedIdState(id);
    },
    [clearBoard],
  );

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
    return () => {
      cancelStatusTimer();
    };
  }, [cancelStatusTimer]);

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

  const refreshAll = useCallback(async () => {
    beginAction("Refreshing…");
    try {
      await refreshList();
      if (selectedId) await refreshDetail(selectedId);
      flashStatus("Refreshed.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Refresh failed");
    }
  }, [refreshList, refreshDetail, selectedId, beginAction, flashStatus]);

  const upload = async (file: File) => {
    setUploading(true);
    beginAction(`Uploading ${file.name} (Phase 1)…`);
    try {
      const accepted = await uploadRfpPdf(file);
      setSelectedIdState(accepted.ticket_id);
      await refreshList();
      await refreshDetail(accepted.ticket_id);
      setStatusMessage("Phase 1 intake started.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const rerun = async () => {
    if (!selectedId) return;
    beginAction("Re-running intake…");
    try {
      await rerunTicket(selectedId);
      await refreshList();
      await refreshDetail(selectedId);
      setStatusMessage("Intake re-run queued.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Re-run failed");
    }
  };

  const startDraft = async (ticketId?: string) => {
    const id = ticketId || selectedId;
    if (!id) return;
    setDrafting(true);
    beginAction("Starting drafting…");
    try {
      setSelectedIdState(id);
      await startDrafting(id);
      await refreshList();
      await refreshDetail(id);
      setStatusMessage("Drafting queued.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Start drafting failed");
    } finally {
      setDrafting(false);
    }
  };

  const redraft = async (departmentId: string) => {
    if (!selectedId) return;
    if (busyDepts.includes(departmentId)) {
      beginAction(`Already re-drafting ${departmentId}…`);
      return;
    }
    setBusyDepts((prev) => [...prev, departmentId]);
    beginAction(`Re-drafting ${departmentId}…`);
    try {
      await redraftSection(selectedId, departmentId);
      await refreshList();
      await refreshDetail(selectedId);
      setStatusMessage(`Re-draft started for ${departmentId}.`);
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Re-draft failed");
    } finally {
      setBusyDepts((prev) => prev.filter((d) => d !== departmentId));
    }
  };

  const releaseRedacted = async (departmentId: string) => {
    if (!selectedId) return;
    if (busyDepts.includes(departmentId)) {
      beginAction(`${departmentId} is busy — try again in a moment.`);
      return;
    }
    setBusyDepts((prev) => [...prev, departmentId]);
    beginAction(`Redacting PHI for ${departmentId}…`);
    try {
      await releaseRedactedSection(selectedId, departmentId);
      await refreshList();
      await refreshDetail(selectedId);
      setStatusMessage(`PHI redacted for ${departmentId}.`);
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Release redacted failed");
    } finally {
      setBusyDepts((prev) => prev.filter((d) => d !== departmentId));
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
    busyDepts,
    upload,
    refreshAll,
    rerun,
    startDraft,
    redraft,
    releaseRedacted,
  };
}
