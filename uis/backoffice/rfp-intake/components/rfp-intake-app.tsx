"use client";

import { RfpTicketDetail } from "./rfp-ticket-detail";
import { RfpTicketList } from "./rfp-ticket-list";
import { RfpUploadForm } from "./rfp-upload-form";
import { useRfpIntake } from "../hooks/use-rfp-intake";

export const RfpIntakeApp = () => {
  const {
    tickets, selectedId, setSelectedId, detail, error, uploading, drafting,
    upload, refreshAll, rerun, startDraft, redraft, releaseRedacted,
  } = useRfpIntake();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">RFP Intake</h1>
        <p className="text-sm text-slate-600">
          Upload institutional RFPs, then start drafting evaluated proposal sections.
        </p>
      </header>
      <RfpUploadForm uploading={uploading} onUpload={(file) => void upload(file)} />
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-slate-800">Tickets</h2>
        <div className="flex gap-3">
          {selectedId ? (
            <button type="button" className="text-sm text-sky-800 underline"
              onClick={() => void rerun()}>Re-run intake</button>
          ) : null}
          <button type="button" className="text-sm text-sky-800 underline"
            onClick={() => void refreshAll()}>Refresh</button>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <RfpTicketList
          tickets={tickets}
          selectedId={selectedId}
          onSelect={setSelectedId}
          draftingId={drafting ? selectedId : null}
          onStartDraft={(id) => void startDraft(id)}
        />
        {detail ? (
          <RfpTicketDetail
            detail={detail}
            drafting={drafting}
            onStartDraft={() => void startDraft()}
            onRedraft={(dept) => void redraft(dept)}
            onReleaseRedacted={(dept) => void releaseRedacted(dept)}
          />
        ) : (
          <p className="text-sm text-slate-500">Select a ticket to view details.</p>
        )}
      </div>
    </div>
  );
};
