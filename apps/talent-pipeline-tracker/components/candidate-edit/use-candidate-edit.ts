import { useState } from "react";

import { useCandidateNotes } from "@/components/candidate-edit/use-candidate-notes";
import { useCandidateProfile } from "@/components/candidate-edit/use-candidate-profile";

export const useCandidateEdit = (id: string, notesOpenByDefault: boolean) => {
  const [statusKind, setStatusKind] = useState<"success" | "error">("success");
  const [reloadVersion, setReloadVersion] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const retryLoad = () => setReloadVersion((value) => value + 1);

  const notify = (kind: "success" | "error", message: string) => {
    setStatusKind(kind);
    setStatusMessage(message);
  };

  const profile = useCandidateProfile(id, reloadVersion, notify, retryLoad);
  const notes = useCandidateNotes(id, reloadVersion, notesOpenByDefault, notify);

  return {
    loading: profile.loading,
    error: profile.error,
    fullName: profile.profile.fullName,
    position: profile.profile.position,
    email: profile.profile.email,
    phone: profile.profile.phone,
    linkedinUrl: profile.profile.linkedinUrl,
    cvUrl: profile.profile.cvUrl,
    experienceYears: profile.profile.experienceYears,
    appliedAt: profile.profile.appliedAt,
    status: profile.profile.status,
    stage: profile.profile.stage,
    notes: notes.notes,
    newNote: notes.newNote,
    isNotesOpen: notes.isNotesOpen,
    saving: profile.saving,
    statusMessage,
    statusKind,
    setStatus: (value: typeof profile.profile.status) => profile.setField("status", value),
    setStage: (value: typeof profile.profile.stage) => profile.setField("stage", value),
    setNewNote: notes.setNewNote,
    setFullName: (value: string) => profile.setField("fullName", value),
    setEmail: (value: string) => profile.setField("email", value),
    setPhone: (value: string) => profile.setField("phone", value),
    setPosition: (value: string) => profile.setField("position", value),
    setLinkedinUrl: (value: string) => profile.setField("linkedinUrl", value),
    setCvUrl: (value: string) => profile.setField("cvUrl", value),
    setExperienceYears: (value: string) => profile.setField("experienceYears", value),
    setIsNotesOpen: notes.setIsNotesOpen,
    savePipeline: profile.savePipeline,
    saveCorrections: profile.saveCorrections,
    addNote: notes.addNote,
    removeNote: notes.removeNote,
    retryLoad,
  };
};
