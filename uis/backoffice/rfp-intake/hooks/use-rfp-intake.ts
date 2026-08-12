"use client";

import { useCallback, useEffect, useState } from "react";

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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [drafting, setDrafting] = useState(false);

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

  const rerun = async () => {
    if (!selectedId) return;
    setError(null);
    try {
      await rerunTicket(selectedId);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-run failed");
    }
  };

  const startDraft = async (ticketId?: string) => {
    const id = ticketId || selectedId;
    if (!id) return;
    setDrafting(true);
    setError(null);
    try {
      setSelectedId(id);
      await startDrafting(id);
      await refreshList();
      await refreshDetail(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Start drafting failed");
    } finally {
      setDrafting(false);
    }
  };

  const redraft = async (departmentId: string) => {
    if (!selectedId) return;
    setError(null);
    try {
      await redraftSection(selectedId, departmentId);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-draft failed");
    }
  };

  const releaseRedacted = async (departmentId: string) => {
    if (!selectedId) return;
    setError(null);
    try {
      await releaseRedactedSection(selectedId, departmentId);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Release redacted failed");
    }
  };

  return {
    tickets,
    selectedId,
    setSelectedId,
    detail,
    error,
    uploading,
    drafting,
    upload,
    refreshAll,
    rerun,
    startDraft,
    redraft,
    releaseRedacted,
  };
}
