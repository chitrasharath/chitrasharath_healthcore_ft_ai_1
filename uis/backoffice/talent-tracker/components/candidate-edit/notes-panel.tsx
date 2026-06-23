import type { CandidateNote } from "@backoffice/talent-tracker/types/candidate";

import { IconButton } from "@backoffice/talent-tracker/components/icon-button";
import { NoteIcon, PlusIcon, TrashIcon } from "@backoffice/talent-tracker/components/icons";

type NotesPanelProps = {
  notes: CandidateNote[];
  newNote: string;
  isNotesOpen: boolean;
  onToggleOpen: () => void;
  onNewNoteChange: (value: string) => void;
  onAddNote: () => void;
  onRemoveNote: (noteId: string) => void;
};

export const NotesPanel = ({
  notes,
  newNote,
  isNotesOpen,
  onToggleOpen,
  onNewNoteChange,
  onAddNote,
  onRemoveNote,
}: NotesPanelProps) => {
  return (
    <section className="rounded-xl border border-[var(--hc-border)] bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <div><h2 className="text-base font-semibold">Notes</h2><p className="text-xs text-[var(--hc-text-muted)]">Notes count: {notes.length}</p></div>
        <IconButton
          type="button"
          compact={false}
          label={isNotesOpen ? "Hide Notes" : "Show Notes"}
          icon={<NoteIcon className="h-4 w-4" />}
          onClick={onToggleOpen}
        />
      </div>

      {isNotesOpen ? (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              value={newNote}
              onChange={(event) => onNewNoteChange(event.target.value)}
              placeholder="Write interview or call note"
              className="w-full rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm"
            />
            <button
              type="button"
              aria-label="Add Note"
              onClick={onAddNote}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[var(--hc-brand)] bg-[var(--hc-brand)] text-white hover:bg-[var(--hc-brand-strong)]"
            >
              <PlusIcon className="h-4 w-4 text-white" />
            </button>
          </div>

          {notes.length === 0 ? <p className="text-sm text-[var(--hc-text-muted)]">No notes yet. Add the first call or interview note to keep context.</p> : (
            notes.map((note) => (
              <article key={note.id} className="rounded-md border border-[var(--hc-border)] p-3 text-sm">
                <p className="mb-1 text-xs text-[var(--hc-text-muted)]">{new Date(note.created_at).toLocaleString()}</p>
                <div className="flex items-start gap-2">
                  <IconButton
                    type="button"
                    label="Remove note"
                    icon={<TrashIcon className="h-4 w-4" />}
                    onClick={() => onRemoveNote(note.id)}
                  />
                  <p className="pt-1">{note.content}</p>
                </div>
              </article>
            ))
          )}
        </div>
      ) : null}
    </section>
  );
};
