"use client";

import { useState } from "react";

import type { DepartmentSection } from "../types/rfp-intake";
import { DEPARTMENT_OWNERS } from "../types/rfp-intake";

type Props = {
  section: DepartmentSection;
  waitingForApproval?: boolean;
  maxIterations?: number;
  busy?: boolean;
  busyDept?: string | null;
  busyDepts?: string[];
  onRedraft?: (departmentId: string) => void;
  onReleaseRedacted?: (departmentId: string) => void;
  onDecide?: (
    departmentId: string,
    decision: "approve" | "reject",
    approver: string,
    reason?: string,
  ) => void;
};

const asList = (value: unknown): string[] =>
  Array.isArray(value) ? value.map(String) : [];

export const RfpSectionPanel = ({
  section,
  waitingForApproval,
  maxIterations = 3,
  busy,
  busyDept,
  busyDepts = [],
  onRedraft,
  onReleaseRedacted,
  onDecide,
}: Props) => {
  const [reason, setReason] = useState("");
  const evals = section.evaluation_results || {};
  const compliance = (evals.compliance || {}) as {
    violations?: { rule_id?: string; message?: string }[];
  };
  const relevance = (evals.relevance || {}) as { missing_aspects?: unknown };
  const missing = asList(relevance.missing_aspects);
  const violations = Array.isArray(compliance.violations) ? compliance.violations : [];
  const containsPhi = Boolean(evals.contains_phi);
  const wasRedacted = Boolean(evals.phi_was_redacted);
  const iteration = section.iteration ?? 0;
  const owner = DEPARTMENT_OWNERS[section.department_id] || "Owner";
  const pendingApproval =
    waitingForApproval && section.approval_status !== "approved" && onDecide;
  const showRelease =
    (containsPhi || section.status === "needs_human_review") && onReleaseRedacted;
  const sectionBusy =
    busyDepts.includes(section.department_id) ||
    Boolean(busy && busyDept === section.department_id);

  return (
    <section className="space-y-2 rounded border border-slate-200 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium capitalize text-slate-900">
          {section.department_id}
          {section.status ? (
            <span className="ml-2 text-xs font-normal text-slate-600">
              ({section.status}
              {iteration ? ` · iter ${iteration}/${maxIterations}` : ""})
            </span>
          ) : null}
          {section.approval_status ? (
            <span className="ml-2 text-xs font-normal text-slate-600">
              approval: {section.approval_status}
            </span>
          ) : null}
        </h3>
        <div className="flex gap-3">
          {showRelease ? (
            <button
              type="button"
              disabled={sectionBusy}
              className="text-xs text-emerald-800 underline disabled:opacity-50"
              onClick={() => onReleaseRedacted?.(section.department_id)}
            >
              {sectionBusy ? "Redacting…" : "Redact PHI & release"}
            </button>
          ) : null}
          {section.status === "needs_human_review" && onRedraft ? (
            <button
              type="button"
              disabled={sectionBusy}
              className="text-xs text-sky-800 underline disabled:opacity-50"
              onClick={() => onRedraft(section.department_id)}
            >
              {sectionBusy ? "Re-drafting…" : "Re-draft"}
            </button>
          ) : null}
        </div>
      </div>
      {wasRedacted ? (
        <p className="text-xs text-amber-800">
          PHI redacted — Compliance review required
          {section.department_id === "compliance" ? " (approve to clear)" : ""}.
        </p>
      ) : null}
      <ul className="list-disc space-y-1 pl-5 text-xs text-slate-700">
        {asList(section.key_aspects).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {section.draft_content ? (
        <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">
          {containsPhi ? "[Redacted draft — PHI blocked]" : section.draft_content}
        </pre>
      ) : null}
      {pendingApproval ? (
        <div className="space-y-2 rounded bg-sky-50 p-2">
          <p className="text-xs text-slate-700">Approver: {owner}</p>
          <textarea
            className="w-full rounded border border-slate-300 p-2 text-xs"
            rows={2}
            placeholder="Reject reason (required for reject)"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy}
              className="rounded bg-emerald-700 px-2 py-1 text-xs text-white disabled:opacity-50"
              onClick={() =>
                onDecide?.(section.department_id, "approve", owner)
              }
            >
              {busy ? "Saving…" : "Approve"}
            </button>
            <button
              type="button"
              disabled={busy || !reason.trim()}
              className="rounded bg-rose-700 px-2 py-1 text-xs text-white disabled:opacity-50"
              onClick={() =>
                onDecide?.(section.department_id, "reject", owner, reason.trim())
              }
            >
              {busy ? "Saving…" : "Reject"}
            </button>
          </div>
        </div>
      ) : section.approval_status === "approved" ? (
        <p className="text-xs font-medium text-emerald-800">
          Approved by {section.approver || owner}
        </p>
      ) : null}
      {evals.feedback_for_generator ? (
        <p className="text-xs text-slate-600">
          Feedback: {String(evals.feedback_for_generator)}
        </p>
      ) : null}
      {missing.length ? (
        <p className="text-xs text-amber-800">Missing: {missing.join("; ")}</p>
      ) : null}
      {violations.length ? (
        <p className="text-xs text-red-800">
          Violations:{" "}
          {violations.map((v) => v.rule_id || v.message).filter(Boolean).join(", ")}
        </p>
      ) : null}
    </section>
  );
};
