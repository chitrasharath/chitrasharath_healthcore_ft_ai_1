"use client";

import { useState } from "react";

import { postMemoryDecision } from "../lib/knowledge-api";
import type { MemoryProposal } from "../types/knowledge";

type Props = {
  proposal: MemoryProposal;
  onDone: (message: string) => void;
};

const ack = (decision: "approve" | "edit" | "reject") =>
  decision === "reject"
    ? "Okay — I won't save that."
    : decision === "edit"
      ? "Saved your edited version."
      : "Saved.";

export const MemoryConsentActions = ({ proposal, onDone }: Props) => {
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState(proposal.text);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (decision: "approve" | "edit" | "reject") => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await postMemoryDecision({
        proposal_id: proposal.id,
        decision,
        edited_text: decision === "edit" ? edited.trim() : undefined,
      });
      onDone(ack(decision));
    } catch {
      setError("Could not save your decision. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-4 dark:border-sky-800 dark:bg-sky-950/40">
      <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Save this memory?</p>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{proposal.text}</p>
      {editing ? (
        <textarea
          aria-label="Edited memory text"
          className="mt-3 w-full rounded-lg border border-slate-300 bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-900"
          rows={3}
          value={edited}
          onChange={(e) => setEdited(e.target.value)}
        />
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" disabled={busy} onClick={() => void run("approve")} className="rounded-lg bg-sky-700 px-3 py-1.5 text-sm text-white disabled:opacity-50">
          Approve
        </button>
        <button
          type="button"
          disabled={busy || (editing && !edited.trim())}
          onClick={() => (editing ? void run("edit") : setEditing(true))}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
        >
          {editing ? "Save edit" : "Edit"}
        </button>
        <button type="button" disabled={busy} onClick={() => void run("reject")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600">
          Reject
        </button>
      </div>
      {error ? <p className="mt-2 text-xs text-red-700 dark:text-red-300" role="alert">{error}</p> : null}
    </div>
  );
};
