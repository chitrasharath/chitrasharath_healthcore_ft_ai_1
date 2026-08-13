"use client";

import { RfpTicketDetail } from "./rfp-ticket-detail";
import { RfpTicketList } from "./rfp-ticket-list";
import { RfpUploadForm } from "./rfp-upload-form";
import { useRfpIntake } from "../hooks/use-rfp-intake";

export const RfpIntakeApp = () => {
  const {
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
  } = useRfpIntake();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">RFP Intake</h1>
        <p className="text-sm text-slate-600">
          Upload RFPs, draft sections, run Phase 3 approvals, and download the final proposal.
        </p>
      </header>
      <RfpUploadForm
        uploading={uploading}
        onUpload={(file) => void upload(file)}
        onRunAll={(file) => void runAll(file)}
      />
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {statusMessage ? <p className="text-sm text-sky-800">{statusMessage}</p> : null}
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-slate-800">Tickets</h2>
        <div className="flex gap-3">
          {selectedId ? (
            <>
              <button
                type="button"
                disabled={busy}
                className="text-sm text-sky-800 underline disabled:opacity-50"
                onClick={() => void rerun()}
              >
                {busy && statusMessage?.startsWith("Re-running")
                  ? "Re-running…"
                  : "Re-run intake"}
              </button>
              <button
                type="button"
                disabled={busy}
                className="text-sm text-rose-800 underline disabled:opacity-50"
                onClick={() => void removeTicket()}
              >
                {busy && statusMessage?.startsWith("Deleting")
                  ? "Deleting…"
                  : "Delete ticket"}
              </button>
            </>
          ) : null}
          <button
            type="button"
            disabled={busy}
            className="text-sm text-sky-800 underline disabled:opacity-50"
            onClick={() => void refreshAll()}
          >
            Refresh
          </button>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <RfpTicketList
          tickets={tickets}
          selectedId={selectedId}
          onSelect={setSelectedId}
          draftingId={drafting ? selectedId : null}
          onStartDraft={(id) => void startDraft(id)}
          onDelete={(id) => void removeTicket(id)}
          busy={busy}
        />
        {detail ? (
          <RfpTicketDetail
            detail={detail}
            drafting={drafting}
            busy={busy}
            busyDept={busyDept}
            busyDepts={busyDepts}
            onStartDraft={() => void startDraft()}
            onContinueToApproval={() => void startDraft(undefined, true)}
            onRunPhase3={() => void runPhase3()}
            onDownload={() => void downloadDocs()}
            onDelete={() => void removeTicket()}
            onRedraft={(dept) => void redraft(dept)}
            onReleaseRedacted={(dept) => void releaseRedacted(dept)}
            onDecide={(dept, decision, approver, reason) =>
              void decide(dept, decision, approver, reason)
            }
          />
        ) : (
          <p className="text-sm text-slate-500">Select a ticket to view details.</p>
        )}
      </div>
    </div>
  );
};
