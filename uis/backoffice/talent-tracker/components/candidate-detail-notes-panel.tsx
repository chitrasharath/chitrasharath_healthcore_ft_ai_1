"use client";

import { useEffect, useRef, useState } from "react";

import { NoteIcon, PlusIcon } from "@backoffice/talent-tracker/components/icons";
import { IconButton } from "@backoffice/talent-tracker/components/icon-button";
import { createNote, getNotes } from "@backoffice/talent-tracker/lib/api";
import type { CandidateNote } from "@backoffice/talent-tracker/types/candidate";

type CandidateDetailNotesPanelProps = {
  candidateId: string;
  openByDefault: boolean;
  autoFocusInput: boolean;
};

export const CandidateDetailNotesPanel = ({
  candidateId,
  openByDefault,
  autoFocusInput,
}: CandidateDetailNotesPanelProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(openByDefault);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [newNote, setNewNote] = useState("");
  const [message, setMessage] = useState("");

  const loadNotes = async () => {
    setLoading(true);
    try {
      const response = await getNotes(candidateId);
      setNotes(response.data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load notes.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;

    getNotes(candidateId)
      .then((response) => {
        if (!active) return;
        setNotes(response.data);
      })
      .catch((error) => {
        if (!active) return;
        setMessage(error instanceof Error ? error.message : "Failed to load notes.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [candidateId]);

  useEffect(() => {
    if (open && autoFocusInput) inputRef.current?.focus();
  }, [open, autoFocusInput]);

  const addNote = async () => {
    if (!newNote.trim()) return;

    try {
      await createNote(candidateId, { content: newNote.trim() });
      setNewNote("");
      setMessage("Note saved.");
      await loadNotes();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to add note.");
    }
  };

  return (
    <section className="rounded-xl border border-[var(--hc-border)] bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">Candidate Notes ({notes.length})</h2>
        <IconButton
          type="button"
          compact={false}
          label={open ? "Hide Notes" : "Show Notes"}
          icon={<NoteIcon className="h-4 w-4" />}
          onClick={() => setOpen((value) => !value)}
        />
      </div>

      {open ? (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={newNote}
              onChange={(event) => setNewNote(event.target.value)}
              placeholder="Write interview or call note"
              className="w-full rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm"
            />
            <button
              type="button"
              aria-label="Add Note"
              onClick={addNote}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[var(--hc-brand)] bg-[var(--hc-brand)] text-white hover:bg-[var(--hc-brand-strong)]"
            >
              <PlusIcon className="h-4 w-4 text-white" />
            </button>
          </div>

          {loading ? <p className="text-sm text-[var(--hc-text-muted)]">Loading notes...</p> : null}
          {!loading && notes.length === 0 ? <p className="text-sm text-[var(--hc-text-muted)]">No notes yet.</p> : null}

          {notes.map((note) => (
            <article key={note.id} className="rounded-md border border-[var(--hc-border)] p-3 text-sm">
              <p className="mb-1 text-xs text-[var(--hc-text-muted)]">{new Date(note.created_at).toLocaleString()}</p>
              <p>{note.content}</p>
            </article>
          ))}
        </div>
      ) : null}

      {message ? <p className="mt-2 text-sm text-[var(--hc-text-muted)]">{message}</p> : null}
    </section>
  );
};