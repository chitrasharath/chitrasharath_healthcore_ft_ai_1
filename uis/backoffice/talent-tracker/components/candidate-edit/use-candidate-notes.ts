import { useEffect, useState } from "react";

import { createNote, deleteNote, getNotes } from "@backoffice/talent-tracker/lib/api";
import type { CandidateNote } from "@backoffice/talent-tracker/types/candidate";

type Notify = (kind: "success" | "error", message: string) => void;

export const useCandidateNotes = (
  id: string,
  reloadVersion: number,
  notesOpenByDefault: boolean,
  notify: Notify,
) => {
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [newNote, setNewNote] = useState("");
  const [isNotesOpen, setIsNotesOpen] = useState(notesOpenByDefault);

  const refreshNotes = async () => {
    const response = await getNotes(id);
    setNotes(response.data);
  };

  useEffect(() => {
    let active = true;

    const loadNotes = async () => {
      try {
        const response = await getNotes(id);
        if (active) setNotes(response.data);
      } catch {
        if (active) setNotes([]);
      }
    };

    loadNotes();
    return () => {
      active = false;
    };
  }, [id, reloadVersion]);

  const addNote = async () => {
    if (!newNote.trim()) return;
    try {
      await createNote(id, { content: newNote.trim() });
      setNewNote("");
      setIsNotesOpen(true);
      await refreshNotes();
      notify("success", "Note added.");
    } catch (addError) {
      notify("error", addError instanceof Error ? addError.message : "Failed to add note.");
    }
  };

  const removeNote = async (noteId: string) => {
    try {
      await deleteNote(id, noteId);
      await refreshNotes();
      notify("success", "Note removed.");
    } catch (removeError) {
      notify("error", removeError instanceof Error ? removeError.message : "Failed to remove note.");
    }
  };

  return { notes, newNote, isNotesOpen, setNewNote, setIsNotesOpen, addNote, removeNote };
};