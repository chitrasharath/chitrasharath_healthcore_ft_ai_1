import { CandidateSummaryCard } from "@backoffice/talent-tracker/components/candidate-summary-card";
import { CandidateCorrectionForm } from "@backoffice/talent-tracker/components/candidate-edit/candidate-correction-form";
import { NotesPanel } from "@backoffice/talent-tracker/components/candidate-edit/notes-panel";
import { PipelineForm } from "@backoffice/talent-tracker/components/candidate-edit/pipeline-form";
import type { useCandidateEdit } from "@backoffice/talent-tracker/components/candidate-edit/use-candidate-edit";

type EditFormSectionsProps = {
  edit: ReturnType<typeof useCandidateEdit>;
};

export const EditFormSections = ({ edit }: EditFormSectionsProps) => {
  const experienceYears = Number.parseInt(edit.experienceYears, 10);

  return (
    <>
      <CandidateSummaryCard
        fullName={edit.fullName}
        position={edit.position}
        email={edit.email}
        phone={edit.phone}
        linkedinUrl={edit.linkedinUrl || null}
        cvUrl={edit.cvUrl || null}
        status={edit.status}
        stage={edit.stage}
        experienceYears={Number.isNaN(experienceYears) ? 0 : experienceYears}
        appliedAt={edit.appliedAt}
      />
      <PipelineForm status={edit.status} stage={edit.stage} saving={edit.saving} onStatusChange={edit.setStatus} onStageChange={edit.setStage} onSave={edit.savePipeline} />
      <CandidateCorrectionForm
        fullName={edit.fullName}
        email={edit.email}
        phone={edit.phone}
        position={edit.position}
        linkedinUrl={edit.linkedinUrl}
        cvUrl={edit.cvUrl}
        experienceYears={edit.experienceYears}
        saving={edit.saving}
        onFullNameChange={edit.setFullName}
        onEmailChange={edit.setEmail}
        onPhoneChange={edit.setPhone}
        onPositionChange={edit.setPosition}
        onLinkedinUrlChange={edit.setLinkedinUrl}
        onCvUrlChange={edit.setCvUrl}
        onExperienceYearsChange={edit.setExperienceYears}
        onSave={edit.saveCorrections}
      />
      <NotesPanel
        notes={edit.notes}
        newNote={edit.newNote}
        isNotesOpen={edit.isNotesOpen}
        onToggleOpen={() => edit.setIsNotesOpen((open) => !open)}
        onNewNoteChange={edit.setNewNote}
        onAddNote={edit.addNote}
        onRemoveNote={edit.removeNote}
      />
    </>
  );
};