"use client";

import { useCallback, useEffect, useState } from "react";

import { getTicket, listTickets, rerunTicket, uploadRfpPdf } from "../lib/rfp-intake-api";
import type { TicketDetail, TicketSummary } from "../types/rfp-intake";

const POLL_MS = 3000;

export function useRfpIntake() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const refreshList = useCallback(async () => {
    const rows = await listTickets();
    setTickets(rows);
  }, []);

  const refreshDetail = useCallback(async (ticketId: string) => {
    const row = await getTicket(ticketId);
    setDetail(row);
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
    const analyzing = tickets.some(
      (t) => t.status === "analyzing" && !t.needs_human_review && t.job_status !== "failed",
    );
    const detailRunning =
      detail?.status === "analyzing" &&
      !detail.needs_human_review &&
      detail.job_status !== "failed";
    if (!analyzing && !detailRunning) {
      return;
    }
    const id = window.setInterval(() => {
      void refreshList().catch(() => undefined);
      if (selectedId) {
        void refreshDetail(selectedId).catch(() => undefined);
      }
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [tickets, detail, selectedId, refreshList, refreshDetail]);

  const refreshAll = useCallback(async () => {
    setError(null);
    try {
      await refreshList();
      if (selectedId) {
        await refreshDetail(selectedId);
      }
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

  return {
    tickets,
    selectedId,
    setSelectedId,
    detail,
    error,
    uploading,
    upload,
    refreshAll,
    rerun,
  };
}
